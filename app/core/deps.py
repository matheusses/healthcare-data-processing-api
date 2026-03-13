"""FastAPI dependencies: get_db and module clients (container + request-scoped session)."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.client import ChatClient
from app.chat.interfaces.client.chat import IChatClient
from app.chat.llm import PatientChatLlm
from app.chat.service import ChatService
from app.config import settings
from app.notes.client import NoteClient
from app.notes.interfaces.client.notes import INoteClient
from app.notes.note_chunk_repository import NoteChunkRepository
from app.notes.repository import NoteRepository
from app.notes.service import NoteService
from app.patients.client import PatientClient
from app.patients.interfaces.client.patients import IPatientClient
from app.patients.repository import PatientRepository
from app.patients.service import PatientService
from app.shared.db.database import get_db_from_factory
from app.shared.llm.client import LLMClient
from app.shared.llm.embeddings import EmbeddingPipeline
from app.summary.client import SummaryClient
from app.summary.interfaces.client.summary import ISummaryClient
from app.summary.llm import SummaryLlm
from app.summary.service import SummaryService


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped DB session from container in app.state."""
    container = request.app.state.container
    session_factory = container.session_factory()
    async for session in get_db_from_factory(session_factory):
        yield session


async def get_patient_client(_: Request, session: AsyncSession = Depends(get_db)) -> IPatientClient:
    """Build PatientClient; session from get_db."""
    patient_repository = PatientRepository(session)
    service = PatientService(patient_repository)
    return PatientClient(service)


async def get_note_client(request: Request, session: AsyncSession = Depends(get_db)) -> INoteClient:
    """Build NoteClient; session from get_db."""
    container = request.app.state.container
    document_storage = container.document_storage()
    document_extractor = container.document_extractor()
    note_repository = NoteRepository(session)
    embedding_pipeline = EmbeddingPipeline(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        embedding_model=settings.VECTOR_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    note_chunk_repository = NoteChunkRepository(session, embedding_pipeline)
    patient_client = await get_patient_client(request, session)
    service = NoteService(
        note_repository,
        patient_client,
        document_storage,
        document_extractor,
        note_chunk_repository,
    )
    return NoteClient(service)


async def get_summary_client(
    request: Request, session: AsyncSession = Depends(get_db)
) -> ISummaryClient:
    """Build SummaryClient with patient client, note client, and SummaryLlm (OPENAI_SUMMARY_MODEL)."""
    patient_client = await get_patient_client(request, session)
    note_client = await get_note_client(request, session)
    llm = LLMClient(
        model=settings.OPENAI_SUMMARY_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        top_p=settings.OPENAI_TOP_P,
    )
    summary_llm = SummaryLlm(llm)
    service = SummaryService(patient_client, note_client, summary_llm)
    return SummaryClient(service)


async def get_chat_client(request: Request, session: AsyncSession = Depends(get_db)) -> IChatClient:
    """Build ChatClient with patient client, note client, and PatientChatLlm (OPENAI_CHAT_MODEL)."""
    patient_client = await get_patient_client(request, session)
    note_client = await get_note_client(request, session)
    llm = LLMClient(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        top_p=settings.OPENAI_TOP_P,
    )
    chat_llm = PatientChatLlm(llm)
    service = ChatService(patient_client, note_client, chat_llm)
    return ChatClient(service)
