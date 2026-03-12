# ADR 001 — Modular Monolith Architecture

## Status

**Accepted**

## Context

The goal of this project is to build a **Healthcare Data Processing API** capable of:

- Managing patients
- Processing medical notes in SOAP format
- Generating structured summaries
- Providing production-grade observability
- Running locally via Docker Compose

**Constraints:**

- Time-boxed implementation (~2 hours)
- Must be clean, testable, and extensible
- Should demonstrate strong backend architecture skills
- Should be production-oriented (observability + performance)

We needed to decide:

- Monolith vs microservices
- Layer structure
- Module communication strategy
- DTO usage
- Observability approach
- Performance strategy

## Decision

### 1. Architectural style

We chose a **Modular Monolith**.

- Each business domain is isolated into modules: **Patients**, **Notes**, **Summary**.
- The system runs as a single deployable unit.

### 2. Module communication rule

- Modules **MUST NOT** import each other directly.
- Modules **MUST** communicate only via their **`client.py`**.
- Modules **MUST** use **DTOs** as contracts.
- This enforces loose coupling and clear boundaries.

### 3. Layered structure per module

Each module follows:

**router → client (deps via parameter) → service → domain → repository**

- **Router**: HTTP handling only; calls Client.
- **Client**: Receives dependencies (services, resources) via parameter; orchestrates and manages services and resources; public facade for the module.
- **Service**: Business orchestration and transaction boundary.
- **Domain**: Core business rules and entities.
- **Repository**: Persistence logic.
- Services control transaction boundaries.

### 4. DTO strategy

DTOs are centralized per module under:

- **`app/shared/schemas/<module>.py`** (e.g. `patients.py`, `notes.py`, `summary.py`).

We use:

- Request DTOs
- Response DTOs
- Internal DTOs (cross-module)

**Rules:**

- Never expose ORM models.
- Never expose domain entities.
- Always use DTOs for cross-layer and cross-module communication.

### 5. Dependency inversion

- Services depend on **repository interfaces** (ABCs in `app/shared/interfaces/`).
- Infrastructure implements those interfaces.
- **Dependency injection** is managed via **dependency-injector** in **`app/core/container.py`** (config, DB session, repositories, services).
- Shared contains base interfaces and DB session factory.

This enforces SOLID principles, especially DIP.

### 6. Database

- **PostgreSQL**
- **Async SQLAlchemy**
- **asyncpg** driver
- Connection pooling enabled
- Indexed columns for performance

### 7. Performance strategy

- **Async-first** architecture.
- **asyncio.gather()** for parallel tasks.
- **Pydantic** (response_model / return type) for all JSON responses; Pydantic v2 uses Rust-based serialization for fast encoding and a single serialization path.
- Structured logging.
- Avoid unnecessary validation in internal flows.

### 8. Observability strategy

The system is observable by default.

**Stack:**

- OpenTelemetry (traces)
- Prometheus (metrics)
- Loki (logs)
- Tempo (trace backend)
- Grafana (visualization)

We instrument:

- FastAPI
- SQLAlchemy
- HTTP calls
- Custom business metrics

### 9. Error handling

- **Global middleware / exception handlers**:
  - `DomainException` → HTTP 400 (or 422 for validation)
  - `UnexpectedException` → HTTP 500
- Structured JSON logs for all errors.

### 10. Containerization

- Multi-stage Docker build.
- Slim base image.
- Cached dependency layers (uv for install).
- **docker-compose** includes:
  - API
  - Postgres
  - Prometheus
  - Loki
  - Tempo
  - Grafana

## Consequences

- Single deployable unit; simpler ops than microservices.
- Clear module boundaries via clients and DTOs; easier to test and later split if needed.
- Centralized DI in `core/container.py` and shared interfaces/schemas simplify wiring and overrides in tests.
- Production-oriented observability and performance from the start.
