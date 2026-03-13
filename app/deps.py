"""FastAPI dependencies: get_db and module clients (container + request-scoped session)."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.client import NoteClient
from app.notes.interfaces.client.notes import INoteClient
from app.notes.repository import NoteRepository
from app.notes.service import NoteService
from app.patients.client import PatientClient
from app.patients.interfaces.client.patients import IPatientClient
from app.patients.repository import PatientRepository
from app.patients.service import PatientService
from app.shared.db.database import get_db_from_factory
from app.shared.llm.embeddings import EmbeddingPipeline


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped DB session from container in app.state."""
    container = request.app.state.container
    session_factory = container.session_factory()
    async for session in get_db_from_factory(session_factory):
        yield session


async def get_patient_client(
    _: Request, session: AsyncSession = Depends(get_db)
) -> IPatientClient:
    """Build PatientClient; session from get_db."""
    patient_repository = PatientRepository(session)
    service = PatientService(patient_repository)
    return PatientClient(service)


async def get_note_client(
    request: Request, session: AsyncSession = Depends(get_db)
) -> INoteClient:
    """Build NoteClient; session from get_db."""
    container = request.app.state.container
    document_storage = container.document_storage()
    document_extractor = container.document_extractor()
    note_repository = NoteRepository(session)
    embedding_pipeline = EmbeddingPipeline(session)
    patient_client = await get_patient_client(request, session)
    service = NoteService(note_repository, patient_client, document_storage, embedding_pipeline, document_extractor)
    return NoteClient(service)
