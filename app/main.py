"""FastAPI app: routers, exception handlers, middleware, startup/shutdown."""

import logging

from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import JSONResponse

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.container import Container
from app.notes.router import router as notes_router
from app.patients.router import router as patients_router
from app.shared.exceptions import DomainException, NotFoundException, UnexpectedException
from app.shared.observability import configure_logging, setup_logger_provider, setup_tracer_provider

logger = logging.getLogger(__name__)

container = Container()
settings = container.config()

configure_logging()
_tracer_provider = setup_tracer_provider(settings)
setup_logger_provider(settings)


def _domain_exception_handler(request: Request, exc: DomainException):
    from fastapi.responses import JSONResponse

    status_code = 422 if exc.code in ("INVALID_FILE_TYPE", "EXTRACTION_ERROR") else 400
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
    )


def _unexpected_exception_handler(request: Request, exc: UnexpectedException):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content={"detail": exc.message or "Internal server error"},
    )

def _not_found_exception_handler(request: Request, exc: NotFoundException):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=404,
        content={"detail": exc.message},
    )

app = FastAPI(
    title="Healthcare Data Processing API",
    description="Modular monolith: patients, notes (SOAP), summaries"
)
app.state.container = container

# Instrument the ASGI app at module setup time so request spans are created
# before serving traffic.
FastAPIInstrumentor.instrument_app(app, tracer_provider=_tracer_provider)

app.add_exception_handler(DomainException, _domain_exception_handler)
app.add_exception_handler(UnexpectedException, _unexpected_exception_handler)
app.add_exception_handler(NotFoundException, _not_found_exception_handler)


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
