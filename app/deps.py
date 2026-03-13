"""FastAPI dependencies: get_db and module clients (container + request-scoped session)."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.client import NoteClient
from app.notes.interfaces.client.notes import INoteClient
from app.patients.client import PatientClient
from app.patients.interfaces.client.patients import IPatientClient
from app.shared.db.database import get_db_from_factory


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped DB session from container in app.state."""
    container = request.app.state.container
    session_factory = container.session_factory()
    async for session in get_db_from_factory(session_factory):
        yield session


async def get_patient_client(
    request: Request, session: AsyncSession = Depends(get_db)
) -> IPatientClient:
    """Build PatientClient; session from get_db."""
    container = request.app.state.container
    repo = container.patient_repository(session)
    service = container.patient_service(patient_repository=repo)
    return PatientClient(service)


async def get_note_client(
    request: Request, session: AsyncSession = Depends(get_db)
) -> INoteClient:
    """Build NoteClient; session from get_db."""
    container = request.app.state.container
    note_repo = container.note_repository(session)
    pacientClient = await get_patient_client(request, session)
    storage = container.document_storage()
    embedding_pipeline = container.embedding_pipeline()
    service = container.note_service(
        note_repository=note_repo,
        patient_client=pacientClient,
        document_storage=storage,
        embedding_pipeline=embedding_pipeline,
        session=session,
    )
    return NoteClient(service)
