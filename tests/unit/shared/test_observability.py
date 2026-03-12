"""Unit tests for observability helpers."""

import logging

from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.config import Settings
from app.shared.observability import (
    _TraceAwareJSONFormatter,
    _build_log_export_endpoint,
    _build_sampler,
    _build_trace_export_endpoint,
    _inject_trace_context_processor,
    _trace_context_filter,
)


def test_build_trace_export_endpoint_converts_default_grpc_port() -> None:
    endpoint = _build_trace_export_endpoint("http://localhost:4317")
    assert endpoint == "http://localhost:4318/v1/traces"


def test_build_trace_export_endpoint_keeps_custom_port() -> None:
    endpoint = _build_trace_export_endpoint("http://otelcol:55681")
    assert endpoint == "http://otelcol:55681/v1/traces"


def test_build_trace_export_endpoint_keeps_existing_traces_path() -> None:
    endpoint = _build_trace_export_endpoint("http://localhost:4318/v1/traces")
    assert endpoint == "http://localhost:4318/v1/traces"


def test_build_log_export_endpoint_appends_path() -> None:
    assert _build_log_export_endpoint("http://localhost:4317") == "http://localhost:4317/v1/logs"
    assert _build_log_export_endpoint("http://localhost:4317/v1/logs") == "http://localhost:4317/v1/logs"


def test_build_sampler_uses_parent_based_ratio() -> None:
    settings = Settings(
        otel_traces_sampler="parentbased_traceidratio",
        otel_traces_sampler_arg="0.25",
    )
    sampler = _build_sampler(settings)

    assert isinstance(sampler, ParentBased)
    assert isinstance(sampler._root, TraceIdRatioBased)
    assert sampler._root.rate == 0.25


def test_build_sampler_clamps_invalid_ratio() -> None:
    settings = Settings(
        otel_traces_sampler="traceidratio",
        otel_traces_sampler_arg="8.0",
    )
    sampler = _build_sampler(settings)

    assert isinstance(sampler, TraceIdRatioBased)
    assert sampler.rate == 1.0


def test_inject_trace_context_processor_leaves_event_dict_unchanged_without_span() -> None:
    """Without an active recording span, trace_id/span_id are not added (avoids logging 0)."""
    event_dict = {"event": "hello", "level": "info"}
    result = _inject_trace_context_processor(None, "info", event_dict)
    assert result["event"] == "hello"
    assert "trace_id" not in result
    assert "span_id" not in result


def test_trace_context_filter_sets_empty_trace_id_without_span() -> None:
    """Without a recording span, filter sets trace_id/span_id to empty on the record."""
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0, msg="hi", args=(), exc_info=None
    )
    assert _trace_context_filter(record) is True
    assert getattr(record, "trace_id", None) == ""
    assert getattr(record, "span_id", None) == ""


def test_trace_aware_json_formatter_includes_trace_id_when_on_record() -> None:
    """Formatter outputs JSON with trace_id/span_id when present on the record."""
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0, msg="hello", args=(), exc_info=None
    )
    record.trace_id = "a" * 32
    record.span_id = "b" * 16
    out = _TraceAwareJSONFormatter().format(record)
    assert "trace_id" in out
    assert "a" * 32 in out
    assert "span_id" in out
    assert "b" * 16 in out
    assert "hello" in out
