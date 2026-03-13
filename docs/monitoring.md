# Monitoring and observability

The Healthcare Data Processing API is instrumented with **OpenTelemetry** and integrates with **Prometheus**, **Loki**, **Tempo**, and **Grafana** when run via Docker Compose (see [Task 004](tasks/004-containerization-and-deployment.md)).

## Architecture

- **API** → sends traces, logs, and (optionally) metrics via OTLP to **OpenTelemetry Collector**.
- **OTel Collector** → exports traces to **Tempo**, logs to **Loki**, and exposes metrics for **Prometheus** (scrape on `otelcol:8889`).
- **Tempo** → runs a **metrics-generator** (span-metrics) and remote-writes latency/throughput/error rate to **Prometheus**.
- **Grafana** → provisioned with datasources for Prometheus, Loki, and Tempo; dashboards for span metrics and API SLO.

## Logs (Loki)

- **Levels**: With default `LOG_LEVEL=INFO`, the API sends **info**, **warn**, **error**, and **exception** (with stack traces) to OTLP; the collector forwards them to Loki. Set `LOG_LEVEL=DEBUG` to include debug logs.
- **Correlation**: Log records include `trace_id` and `span_id` when emitted inside a request span, so in Grafana you can jump from a Tempo span to “Logs for this span” in Loki.

## Traces (Tempo) and database instrumentation

- **HTTP**: FastAPI is instrumented so each request creates a trace with span names derived from the route.
- **Database**: SQLAlchemy (async) is instrumented so each DB operation (query, commit, etc.) appears as a **child span** of the request trace. In Tempo you can see request → DB spans and their duration.

## Key endpoints and ports

| Service   | Port | Purpose                          |
|----------|------|----------------------------------|
| API      | 8000 | Health, docs, application       |
| Grafana  | 3000 | Dashboards and Explore           |
| Prometheus | 9090 | Metrics and PromQL               |
| OTel Collector | 4317 (gRPC), 8889 (metrics) | OTLP ingest, metrics scrape |
| Loki     | 3100 | Logs                             |
| Tempo    | 3200 | Traces                           |

## Prometheus metrics

- **From OTel Collector** (scrape job `otelcol`): any metrics the API or collector exports (e.g. request counts, duration) on port 8889.
- **From Tempo (remote_write)**:
  - `traces_spanmetrics_calls_total` — request throughput by service.
  - `traces_spanmetrics_latency_bucket` — latency histogram; use `histogram_quantile(0.95, ...)` for p95, etc.
  - `traces_spanmetrics_latency_bucket` with status code can be used for error rate (e.g. 5xx).

These appear in Prometheus after Tempo has processed spans and remote-written; allow 1–2 minutes after traffic.

## Grafana dashboards

- **Observability → Span metrics (Tempo → Prometheus)** — throughput, p99 latency, and a check that span-metrics exist.
- **Observability → API SLO** — SLO-oriented panels: p95 latency, error rate (from span-metrics), request rate. Use for availability and latency targets.

## SLO-oriented metrics (API)

The **API SLO** dashboard uses Tempo’s span-metrics in Prometheus:

- **Latency (p95)**: `histogram_quantile(0.95, sum(rate(traces_spanmetrics_latency_bucket[5m])) by (le, service))`
- **Request rate**: `sum(rate(traces_spanmetrics_calls_total[5m])) by (service)`
- **Error rate**: From span-metrics with status (if configured) or from logs/traces; the dashboard includes a placeholder/example.

Define your targets (e.g. p95 &lt; 500 ms, error rate &lt; 0.1%) in runbooks and alerting rules.

## Verification

1. Start the stack: `docker compose up -d` and run `./scripts/initial_db.sh`.
2. Send traffic to the API (e.g. `GET /docs`, `GET /patients/`).
3. In Grafana (http://localhost:3000): open **Explore → Prometheus**, query `traces_spanmetrics_calls_total` (may need to type the name; wait 1–2 min).
4. Open **Observability → API SLO** (or Span metrics) and confirm panels show data for the selected time range.

## Troubleshooting

- **“No data” in span-metrics**: Ensure Tempo has `span-metrics` in `overrides.defaults.metrics_generator.processors` (see `observability/tempo.yml`), restart Tempo, send traffic, wait 1–2 minutes.
- **Grafana metric dropdown empty**: Remote-written metrics may not appear in the dropdown; type the metric name in Explore (e.g. `traces_spanmetrics_calls_total`).
- **Logs and traces**: Use **Explore → Loki** for logs (with `trace_id` in JSON) and **Explore → Tempo** for traces; use “Logs for this span” in Tempo to jump to Loki.

## Security

- Do not log PHI/PII or full request/response bodies.
- In production, disable anonymous access in Grafana and use proper auth and TLS for Prometheus/Grafana/OTel Collector.
