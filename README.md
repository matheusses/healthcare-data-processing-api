# Healthcare Data Processing API

Modular monolith API for **patients**, **medical notes** (SOAP), and **structured summaries**, with production-oriented observability (OpenTelemetry, Prometheus, Loki, Tempo, Grafana).

## Overview

- **Architecture**: [ADR 001 — Modular Monolith](docs/adr/001-modular-monolith-architecture.md). Modules: Patients, Notes, Summary. Communication only via `client.py` and DTOs.
- **Stack**: FastAPI, async SQLAlchemy (PostgreSQL/asyncpg), Pydantic, dependency-injector, OpenTelemetry.
- **Endpoints**: `/patients/` (CRUD, list), `/patients/{patient_id}/notes/` (upload, list, delete).

## Setup

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/).

**Python version (pyenv):** This project pins 3.12 in `.python-version`. If you use [pyenv](https://github.com/pyenv/pyenv), run `pyenv install -s` in the repo to install the right interpreter, then `pyenv local` is already set.

**Install dependencies with uv:** uv uses your current Python (e.g. from pyenv) to create a venv and install from `pyproject.toml` + lockfile.

```bash
uv sync
cp .env.example .env
# Edit .env: set DATABASE_URL (PostgreSQL), DOCUMENT_STORAGE_* (MinIO), and optionally OTEL_*, OPENAI_API_KEY for embeddings.
# For Docker Compose provisioning, you can also set MINIO_ROOT_USER and MINIO_ROOT_PASSWORD.
```

For OTLP in local development:
- `OTEL_EXPORTER_OTLP_ENDPOINT` should point to collector gRPC (default `http://localhost:4317`).
- Traces are sent via HTTP to the derived `/v1/traces` endpoint.
- `OTEL_TRACES_SAMPLER` / `OTEL_TRACES_SAMPLER_ARG` control trace sampling ratio.

### Initial DB setup

After starting Postgres (e.g. `docker compose up -d`), run the initial DB script to wait for the database and apply migrations:

```bash
./scripts/initial_db.sh
```

This loads `.env`, waits for Postgres at `localhost:5434` (or `PGHOST`/`PGPORT`), then runs `alembic upgrade head`. It uses `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` to build `DATABASE_URL` if needed.

### Database migrations (Alembic)

Migrations use the same `DATABASE_URL` as the app (PostgreSQL/asyncpg). From the project root:

```bash
# Apply all pending migrations (requires running Postgres)
uv run alembic upgrade head

# Generate a new revision after changing app/shared/models.py
uv run alembic revision --autogenerate -m "description of change"

# Roll back one revision
uv run alembic downgrade -1

# Emit SQL only (no DB connection)
uv run alembic upgrade head --sql
```

`pg_trgm` is enabled by migration `656dcd0fa7a3` and is required for ranked fuzzy search on `/patients/`. Migration `a1b2c3d4e5f6` creates the `notes` table; `b2c3d4e5f6a7` enables the `vector` extension and creates the `note_chunks` table (pgvector) for embedding storage. **pgvector:** When using Docker Compose, the `postgres` service uses `pgvector/pgvector:pg16` so the extension is available. If you run migrations against a local PostgreSQL (e.g. system-installed), install the [pgvector](https://github.com/pgvector/pgvector) extension on that server first, or migrations will fail at `CREATE EXTENSION vector`.

**Security:** Never commit secrets in migration scripts. Use environment-based config only.

## Run

**Local (no Docker):**

```bash
uv run fastapi dev
```

API: `http://127.0.0.1:8000`. Docs: `http://127.0.0.1:8000/docs`.

**With Docker Compose (API + Postgres + observability stack):**

```bash
docker compose up -d
# Apply migrations and ensure DB is ready (waits for Postgres, then runs Alembic)
./scripts/initial_db.sh
# API on :8000, Grafana on :3000, Prometheus :9090, etc.
```

The Postgres healthcheck uses `POSTGRES_USER` (e.g. `user`); ensure `.env` has `POSTGRES_USER` and `POSTGRES_DB=healthcare` so the default user exists (the image creates one role from `POSTGRES_USER`, not from the DB name).

**MinIO (document storage):** With Docker Compose, MinIO runs on port 9000 and is provisioned automatically by the `minio-provision` service. It creates the bucket and grants `readwrite` policy to `DOCUMENT_STORAGE_ACCESS_KEY` (if different from root), so the API can upload and create buckets. Set `DOCUMENT_STORAGE_ENDPOINT`, `DOCUMENT_STORAGE_BUCKET`, `DOCUMENT_STORAGE_ACCESS_KEY`, `DOCUMENT_STORAGE_SECRET_KEY` (and optionally `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`) in `.env` (see `.env.example`). The API uses MinIO for file-backed note uploads (`POST /patients/{id}/notes/upload`). Upload accepts `.txt`, `.pdf`, and handwritten/printed images (`.jpg`, `.png`); PDF and images are processed with LangChain (PyPDF, RapidOCR) — no extra system dependencies.

### Observability troubleshooting

- If Grafana Tempo TraceQL metrics queries fail with `error finding generators ... empty ring`, restart the observability stack so Tempo picks up the `metrics_generator` ring config:

  ```bash
  docker compose up -d --force-recreate tempo prometheus otelcol grafana
  ```

- Example query that depends on the generator ring:

  ```traceql
  {resource.service.name != nil} | quantile_over_time(duration, 0.9) by(resource.service.name)
  ```

- **Why trace_id/span_id can be 0 or missing**: They appear as 0 when there is no active OpenTelemetry span (e.g. logs during startup, lifespan, or outside request handling). The default “no span” context in the SDK has trace_id=0, span_id=0. Structlog is configured to omit trace_id/span_id for that case so you don’t see 0 in JSON logs; only request-scoped logs get those fields. If *request* logs still show 0, ensure `FastAPIInstrumentor.instrument_app(app)` is called at module level in `app/main.py` (outside lifespan) and restart the API.

- **Log relation by trace_id**: Logs are correlated with traces so you can move between Loki and Tempo in Grafana. Every request-scoped log (structlog and stdlib) includes `trace_id` (and `span_id`) in the JSON body. In Grafana: (1) **Log → Trace**: in Explore → Loki, the `trace_id` value in a log line is a link to the trace in Tempo. (2) **Trace → Logs**: in Explore → Tempo, open a trace and use "Logs for this span" to query Loki for logs with that `trace_id` (via `tracesToLogsV2` query).

- **Grafana “does not recognize” traces_spanmetrics_calls_total / traces_spanmetrics_latency_bucket**: These metrics are written by Tempo’s metrics-generator (remote_write) into Prometheus. Grafana’s metric dropdown often does not list metrics that have no series yet or that come only from remote write. (1) Open the provisioned dashboard **Observability → Span metrics (Tempo → Prometheus)**; if panels show “No data”, the metrics are not in Prometheus yet — ensure Tempo has `span-metrics` in `overrides.defaults.metrics_generator.processors`, restart Tempo, send API traffic, and wait 1–2 minutes. (2) In **Explore → Prometheus**, type the metric name yourself (e.g. `traces_spanmetrics_calls_total`) in the query field; do not rely only on the metric dropdown. (3) Use a time range that includes recent traffic (e.g. “Last 15 minutes”).

## Testing

- **Unit tests** (no DB): schemas, domain, services with mocked repos.

  ```bash
  uv run pytest tests/unit/
  ```

- **Integration tests** (need Postgres): set `DATABASE_URL` to a running instance, then:

  ```bash
  uv run pytest tests/integration/
  ```

- **Functional tests**: OpenAPI and route checks run without DB; one test requires DB and is skipped if unavailable.

  ```bash
  uv run pytest tests/functional/
  ```

- **All tests (excluding DB-dependent):**

  ```bash
  uv run pytest
  ```

- **With coverage:**

  ```bash
  uv run pytest tests/unit/ tests/functional/ --cov=app --cov-report=term-missing
  ```

## Security

- **Secrets**: Do not commit `.env` or any secrets. Use `.env.example` as reference only.
- **Input validation**: All request bodies validated via Pydantic; string length and format constraints on DTOs.
- **OWASP**: Least-privilege, no raw SQL from user input, structured error responses (no stack traces to client).
- **PHI/PII**: Notes contain PHI; avoid logging note content or patient identifiers. Observability uses structured logs with trace IDs; do not log request bodies that include clinical text.
- **Supply chain**: Dependencies managed with `uv`; run `uv sync` and keep `uv.lock` in version control.
- **Notes and storage**: Document storage credentials (MinIO/S3) must not be committed; use env vars. Embedding pipeline is optional (set `OPENAI_API_KEY` to enable); vector data is stored in Postgres (pgvector).

**Security contact:** See [CODEOWNERS](CODEOWNERS) for ownership and responsible disclosure.

## Documentation

- [ADR 001 — Modular Monolith Architecture](docs/adr/001-modular-monolith-architecture.md)
- [Task 001 — Boilerplate implementation](docs/tasks/001-healthcare-api-boilerplate.md)
- [Task 002 — Patient Notes API and vector storage](docs/tasks/002-patient-notes-api.md)
- [Notes API usage](docs/notes-api.md) (SOAP context and endpoints)

## License

See repository license file.
