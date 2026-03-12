"""Dependency-injector Container: config, DB session factory, repositories, services."""

from dependency_injector import containers, providers

from app.config import Settings
from app.patients.repository import PatientRepository
from app.patients.service import PatientService
from app.shared.db.database import build_engine, build_session_factory


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

    # Repositories (Factory: call with session from get_db)
    patient_repository = providers.Factory(PatientRepository)

    # Services (Factory: call with repo instances created from request-scoped session)
    patient_service = providers.Factory(PatientService)
