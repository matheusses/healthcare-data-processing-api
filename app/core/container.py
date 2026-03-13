"""Dependency-injector Container: config, DB session factory, repositories, services."""

from dependency_injector import containers, providers

from app.config import Settings
from app.notes.repository import NoteRepository
from app.notes.service import NoteService
from app.patients.repository import PatientRepository
from app.patients.service import PatientService
from app.shared.db.database import build_engine, build_session_factory
from app.shared.llm.embeddings import EmbeddingPipeline
from app.shared.storage.document_storage import DocumentStorageClient


class Container(containers.DeclarativeContainer):
    """Application container. Session is request-scoped via get_db; repos need session from Depends."""

    config = providers.Singleton(Settings)

    engine = providers.Singleton(
        build_engine,
        settings=config,
    )

    session_factory = providers.Singleton(
        build_session_factory,
        engine=engine,
    )

    # Document storage (MinIO/S3)
    document_storage = providers.Singleton(DocumentStorageClient, settings=config)

    # Embedding pipeline (optional; requires OPENAI_API_KEY for embeddings)
    embedding_pipeline = providers.Singleton(EmbeddingPipeline, settings=config)

    # Repositories (Factory: call with session from get_db)
    patient_repository = providers.Factory(PatientRepository)
    note_repository = providers.Factory(NoteRepository)

    # Services (Factory: call with repo instances created from request-scoped session)
    patient_service = providers.Factory(PatientService)
    note_service = providers.Factory(
        NoteService,
        note_repository=note_repository,
        patient_repository=patient_repository,
        document_storage=document_storage,
        embedding_pipeline=embedding_pipeline,
    )
