"""Dependency-injector Container: config, DB session factory, repositories, services."""

from app.shared.document_loading.extractor import DocumentExtractor
from dependency_injector import containers, providers

from app.config import Settings
from app.shared.db.database import build_engine, build_session_factory
from app.shared.storage.document_storage import DocumentStorageClient


class Container(containers.DeclarativeContainer):
    """Application container. Session is request-scoped via get_db; repos need session from Depends."""
    config = providers.Singleton(Settings)

    settings = providers.Singleton(Settings)

    # database
    engine = providers.Singleton(
        build_engine,
        settings=settings,
    )

    session_factory = providers.Singleton(
        build_session_factory,
        engine=engine,
    )
    
    # infrastructure resources(shared)
    document_storage = providers.Factory(DocumentStorageClient)
    document_extractor = providers.Factory(DocumentExtractor)