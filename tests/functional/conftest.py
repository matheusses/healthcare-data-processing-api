"""Functional test client and overrides."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


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
