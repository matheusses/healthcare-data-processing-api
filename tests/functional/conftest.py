"""Functional test client and overrides."""

import os
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.main import app


async def _mock_get_db():
    """Yield a mock AsyncSession so routes can run without a real DB (e.g. for 422 validation tests)."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)
    session.close = AsyncMock(return_value=None)
    try:
        yield session
    finally:
        pass


@pytest.fixture
def client():
    """FastAPI TestClient with get_db overridden so DB-dependent routes run without a real DB."""
    app.dependency_overrides[get_db] = _mock_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client_with_lifespan():
    """TestClient with lifespan (requires DATABASE_URL to a running Postgres). Skips if DB unavailable."""
    url = os.environ.get("DATABASE_URL", "")
    if not url.strip().startswith("postgresql+asyncpg://"):
        pytest.skip(
            "Set DATABASE_URL to postgresql+asyncpg://... for functional tests that need a real DB"
        )
    try:
        with TestClient(app) as c:
            yield c
    except Exception as e:
        pytest.skip(f"DB not available for functional test: {e}")


@pytest.fixture
def auth_headers():
    """Placeholder for future auth."""
    return {}
