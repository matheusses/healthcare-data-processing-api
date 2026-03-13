"""Functional test client and overrides."""

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import app
from app.notes.service import NoteService


@pytest.fixture(scope="session", autouse=True)
def _patch_container_note_service():
    """Ensure note_service is built without patient_repository (session comes from get_note_client)."""
    container = app.state.container
    container.note_service = providers.Factory(
        NoteService,
        note_repository=container.note_repository,
        document_storage=container.document_storage,
        embedding_pipeline=container.embedding_pipeline,
    )
    yield


@pytest.fixture
def client():
    """FastAPI TestClient. Without lifespan so tests that only need OpenAPI pass without DB."""
    return TestClient(app)


@pytest.fixture
def client_with_lifespan():
    """TestClient with lifespan (requires DATABASE_URL to a running Postgres). Skips if DB unavailable."""
    try:
        with TestClient(app) as c:
            yield c
    except Exception as e:
        pytest.skip(f"DB not available for functional test: {e}")


@pytest.fixture
def auth_headers():
    """Placeholder for future auth."""
    return {}
