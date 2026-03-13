"""FastAPI app: routers, exception handlers, middleware, lifespan."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.chat.router import router as chat_router
from app.core.container import Container
from app.notes.router import router as notes_router
from app.patients.router import router as patients_router
from app.summary.router import router as summary_router
from app.shared.exceptions import DomainException, NotFoundException
from app.shared.observability import (
    configure_langsmith_tracing,
    configure_logging,
    instrument_httpx,
    setup_logger_provider,
    setup_tracer_provider,
)

logger = logging.getLogger(__name__)

container = Container()
settings = container.config()

configure_logging(settings)
# Enable LangSmith for LangChain runs before any LLM code runs
configure_langsmith_tracing(settings)
_tracer_provider = setup_tracer_provider(settings)
setup_logger_provider(settings)
instrument_httpx()  # Outbound HTTP (e.g. LLM) traced after TracerProvider is set


def _domain_exception_handler(request: Request, exc: DomainException):
    from fastapi.responses import JSONResponse

    status_code = 422 if exc.code in ("INVALID_FILE_TYPE", "EXTRACTION_ERROR") else 400
    logger.error(
        "Domain exception: %s (code=%s)",
        exc.message,
        exc.code,
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
    )


def _unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def _not_found_exception_handler(request: Request, exc: NotFoundException):
    from fastapi.responses import JSONResponse

    logger.error(
        "Not found: %s (path=%s)",
        exc.message,
        request.url.path,
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message},
    )


def _validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log 422 validation errors so they appear in Grafana/Loki (no PII/PHI in logs)."""
    errors = exc.errors()
    logger.error(
        "Request validation failed: path=%s method=%s error_count=%s",
        request.url.path,
        request.method,
        len(errors),
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": 422,
            "error_count": len(errors),
            "errors": errors,
        },
    )
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": errors}),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB engine so SQLAlchemy instrumentation uses the global TracerProvider.

    DB spans (with db.statement query text) then export correctly. Skipped when
    DATABASE_URL is unset.
    """
    if settings.database_url:
        _ = container.engine()
    yield


app = FastAPI(
    title="Healthcare Data Processing API",
    description="Modular monolith: patients, notes (SOAP), summaries",
    lifespan=lifespan,
)
app.state.container = container


# Instrument the ASGI app at module setup time so request spans are created
# before serving traffic.
FastAPIInstrumentor.instrument_app(app, tracer_provider=_tracer_provider)

app.add_exception_handler(DomainException, _domain_exception_handler)
app.add_exception_handler(NotFoundException, _not_found_exception_handler)
app.add_exception_handler(RequestValidationError, _validation_exception_handler)
app.add_exception_handler(Exception, _unexpected_exception_handler)


main_router = APIRouter()


@main_router.get("/health", tags=["health"], summary="Health check", response_class=JSONResponse)
async def healthcheck():
    """
    Health check endpoint for liveness/readiness probes.
    Returns 200 with {"status": "ok"} if the API is running.
    """
    logger.info("Health check endpoint called")
    return {"status": "ok"}


app.include_router(main_router)
app.include_router(patients_router)
app.include_router(notes_router)
app.include_router(summary_router)
app.include_router(chat_router)
