"""OpenTelemetry observability: tracing, logging, and trace-context correlation.

This module configures:

- **TracerProvider**: OTLP trace export (HTTP), configurable sampling, and
  resource attributes (service.name, deployment.environment) from application
  settings.
- **LoggerProvider**: OTLP log export (gRPC) and a bridge from the standard
  logging subsystem so that all log records can be exported and correlated
  with trace IDs.
- **Structured logging**: structlog with JSON output and optional injection
  of trace_id/span_id from the current OpenTelemetry span context.

All behavior is driven by :class:`app.config.Settings`; no endpoints, ports,
or security options are hardcoded. OTLP paths follow the OpenTelemetry
specification and are defined as module constants for consistency and tests.

Security considerations:
- Do not log PII/PHI; use structured fields and redaction where needed.
- Prefer ``otel_exporter_otlp_insecure=False`` in production (TLS to the collector).
- Sampling (e.g. traceidratio) helps control volume and cost; tune via settings.
"""

import json
import logging
from typing import Any
from urllib.parse import urlparse

import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)

from app.config import Settings

# --- OTLP path constants (OpenTelemetry spec) ---------------------------------
# Used to build HTTP/gRPC endpoints from the base URL in settings; avoids
# scattering magic strings and eases testing and protocol changes.
OTLP_HTTP_TRACES_PATH = "/v1/traces"
OTLP_HTTP_LOGS_PATH = "/v1/logs"

# Default OTLP ports: gRPC 4317, HTTP 4318 (used when normalizing base URLs).
_DEFAULT_OTLP_GRPC_PORT = "4317"
_DEFAULT_OTLP_HTTP_PORT = "4318"


def _build_trace_export_endpoint(base_endpoint: str) -> str:
    """Build the OTLP HTTP traces endpoint from a base URL.

    Normalizes the base endpoint for HTTP OTLP: if the authority uses the
    standard gRPC port (4317), it is converted to the HTTP port (4318).
    Then the standard traces path is appended if not already present.

    Args:
        base_endpoint: Base OTLP endpoint from config (e.g. OTEL_EXPORTER_OTLP_ENDPOINT).

    Returns:
        Full URL for the trace exporter, e.g. ``http://localhost:4318/v1/traces``.
    """
    if not base_endpoint or not base_endpoint.strip():
        return ""
    parsed = urlparse(base_endpoint.strip())
    netloc = parsed.netloc or parsed.path
    path = parsed.path.rstrip("/") if parsed.path else ""

    # Normalize gRPC default port to HTTP default for trace exporter (HTTP).
    if netloc.endswith(f":{_DEFAULT_OTLP_GRPC_PORT}"):
        netloc = netloc[: -len(f":{_DEFAULT_OTLP_GRPC_PORT}")] + f":{_DEFAULT_OTLP_HTTP_PORT}"

    if path.endswith(OTLP_HTTP_TRACES_PATH):
        full_path = path
    else:
        full_path = f"{path.rstrip('/')}/{OTLP_HTTP_TRACES_PATH}".lstrip("/") or OTLP_HTTP_TRACES_PATH
    if not full_path.startswith("/"):
        full_path = "/" + full_path
    scheme = parsed.scheme or "http"
    return f"{scheme}://{netloc}{full_path}"


def _build_log_export_endpoint(base_endpoint: str) -> str:
    """Build the OTLP logs endpoint from a base URL.

    Appends the standard logs path if not already present. Used for the
    log exporter endpoint derived from the same base as traces.

    Args:
        base_endpoint: Base OTLP endpoint from config.

    Returns:
        Full URL for the log exporter, e.g. ``http://localhost:4317/v1/logs``.
    """
    if not base_endpoint or not base_endpoint.strip():
        return ""
    parsed = urlparse(base_endpoint.strip())
    netloc = parsed.netloc or parsed.path
    path = (parsed.path or "").rstrip("/")

    if path.endswith(OTLP_HTTP_LOGS_PATH):
        full_path = path
    else:
        full_path = f"{path.rstrip('/')}/{OTLP_HTTP_LOGS_PATH}".lstrip("/") or OTLP_HTTP_LOGS_PATH
    if not full_path.startswith("/"):
        full_path = "/" + full_path
    scheme = parsed.scheme or "http"
    return f"{scheme}://{netloc}{full_path}"


def _trace_context_filter(record: logging.LogRecord) -> bool:
    """Attach trace_id and span_id to the log record when in a recording span.

    Lets formatters use %(trace_id)s and %(span_id)s so OTLP log body and Loki
    store them for log↔trace correlation in Grafana.
    """
    span = trace.get_current_span()
    if not span.is_recording():
        setattr(record, "trace_id", "")
        setattr(record, "span_id", "")
        return True
    ctx = span.get_span_context()
    if ctx.trace_id == 0 and ctx.span_id == 0:
        setattr(record, "trace_id", "")
        setattr(record, "span_id", "")
        return True
    setattr(record, "trace_id", format(ctx.trace_id, "032x"))
    setattr(record, "span_id", format(ctx.span_id, "016x"))
    return True


class _TraceAwareJSONFormatter(logging.Formatter):
    """Format log records as one-line JSON with trace_id/span_id when present."""

    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        out: dict[str, Any] = {
            "message": msg,
            "level": record.levelname,
            "logger": record.name,
        }
        trace_id = getattr(record, "trace_id", None) or ""
        span_id = getattr(record, "span_id", None) or ""
        if trace_id:
            out["trace_id"] = trace_id
        if span_id:
            out["span_id"] = span_id
        if record.exc_info:
            out["exception"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def _inject_trace_context_processor(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor: add trace_id and span_id to the event dict when in a recording span.

    Only injects when the current span is recording and has a non-zero trace_id
    (invalid/default span context uses 0). This avoids logging trace_id=0/span_id=0
    when there is no active request span (e.g. startup, lifespan, or before instrumentation).
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict
    ctx = span.get_span_context()
    if ctx.trace_id == 0 and ctx.span_id == 0:
        return event_dict
    event_dict["trace_id"] = format(ctx.trace_id, "032x")
    event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging() -> None:
    """Configure structlog and instrument standard logging for OTEL context.

    - Injects OpenTelemetry context into the standard logging format when
      LoggingInstrumentor is used.
    - Adds trace_id/span_id to every structlog event when inside a recording span
      (request handlers); omits them when no active span or context is invalid (0).
    """
    LoggingInstrumentor().instrument(set_logging_format=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_trace_context_processor,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_trace_context_to_logs(processor: Any) -> Any:
    """Add trace_id and span_id to log records when in an active OTEL span.

    Intended for use as a structlog processor or similar pipeline step so
    that logs emitted within a trace automatically carry trace and span
    identifiers for correlation in the backend.

    Args:
        processor: Next processor in the chain (pass-through).

    Returns:
        The same processor, for chaining.
    """
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        structlog.contextvars.bind_contextvars(
            trace_id=format(ctx.trace_id, "032x"),
            span_id=format(ctx.span_id, "016x"),
        )
    return processor


def setup_tracer_provider(settings: Settings) -> TracerProvider:
    """Create and register the global TracerProvider with OTLP export when configured.

    Resource attributes (service.name, deployment.environment) and the
    trace sampler are taken from settings. If ``otel_exporter_otlp_endpoint``
    is set, an HTTP OTLP span exporter is added so traces are sent to the
    collector.

    Args:
        settings: Application settings (OTEL_* and environment).

    Returns:
        The configured TracerProvider (also set as the global provider).
    """
    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )
    provider = TracerProvider(resource=resource, sampler=_build_sampler(settings))

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        trace_endpoint = _build_trace_export_endpoint(settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        if trace_endpoint:
            exporter = OTLPSpanExporter(endpoint=trace_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logging.getLogger(__name__).info(
                "OTLP trace exporter configured (HTTP): %s", trace_endpoint
            )

    trace.set_tracer_provider(provider)
    return provider


def setup_logger_provider(settings: Settings) -> LoggerProvider:
    """Create and optionally register the global LoggerProvider with OTLP log export.

    Resource attributes come from settings. If ``otel_exporter_otlp_endpoint``
    is set, logs are exported via OTLP (gRPC) to that endpoint; TLS is
    controlled by ``otel_exporter_otlp_insecure``. A LoggingHandler is
    always added so that standard logging (and structlog when using the
    standard logger) is bridged to the LoggerProvider for export and
    trace correlation.

    Args:
        settings: Application settings (OTEL_* and environment).

    Returns:
        The configured LoggerProvider (and set as global when OTLP is enabled).
    """
    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )
    logger_provider = LoggerProvider(resource=resource)

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        log_endpoint = _build_log_export_endpoint(settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        if log_endpoint:
            log_exporter = OTLPLogExporter(
                endpoint=log_endpoint,
                insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
            )
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
            set_logger_provider(logger_provider)

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    handler.addFilter(_trace_context_filter)
    handler.setFormatter(_TraceAwareJSONFormatter())
    logging.getLogger().addHandler(handler)

    return logger_provider


def _build_sampler(settings: Settings) -> Sampler:
    """Build the trace sampler from OTEL_TRACES_SAMPLER and OTEL_TRACES_SAMPLER_ARG.

    Supported sampler names (case-insensitive): always_on, always_off,
    traceidratio, parentbased_traceidratio (and common variants). For
    ratio-based samplers, the argument is parsed and clamped to [0.0, 1.0].
    Unknown names fall back to parentbased_traceidratio with the configured ratio.

    Args:
        settings: Application settings for sampler name and argument.

    Returns:
        A Sampler instance for the TracerProvider.
    """
    sampler_name = (settings.OTEL_TRACES_SAMPLER or "").lower().strip()
    ratio = _safe_trace_ratio(settings.OTEL_TRACES_SAMPLER_ARG)

    if sampler_name in {"always_on", "alwayson"}:
        return ALWAYS_ON
    if sampler_name in {"always_off", "alwaysoff"}:
        return ALWAYS_OFF
    if sampler_name in {"traceidratio", "traceidratio-based", "traceidratio_based"}:
        return TraceIdRatioBased(ratio)
    if sampler_name in {
        "parentbased_traceidratio",
        "parentbased_traceidratio_based",
        "parentbasedtraceidratio",
    }:
        return ParentBased(root=TraceIdRatioBased(ratio))

    logging.getLogger(__name__).warning(
        "Unknown OTEL_TRACES_SAMPLER '%s'; using parentbased_traceidratio.",
        settings.otel_traces_sampler,
    )
    return ParentBased(root=TraceIdRatioBased(ratio))


def _safe_trace_ratio(raw_ratio: str) -> float:
    """Parse sampling ratio from config and clamp to [0.0, 1.0].

    Invalid or missing values log a warning and return 1.0 (sample all).
    """
    try:
        ratio = float(raw_ratio)
    except (TypeError, ValueError):
        logging.getLogger(__name__).warning(
            "Invalid OTEL_TRACES_SAMPLER_ARG '%s'; defaulting to 1.0.",
            raw_ratio,
        )
        return 1.0
    return max(0.0, min(1.0, ratio))
