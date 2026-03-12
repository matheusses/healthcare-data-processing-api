"""Integration test DB session, engine, fixtures."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.shared.db.database import Base



@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def settings():
    return Settings()


@pytest.fixture(scope="session")
def engine(settings):
    url = settings.database_url
    if "sqlite" in url or url == "postgresql+asyncpg://user:password@localhost:5432/healthcare":
        pytest.skip("Set DATABASE_URL to a real Postgres for integration tests")
    return create_async_engine(url, pool_pre_ping=True, echo=False)


@pytest.fixture(scope="session")
def session_factory(engine):
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
async def _tables(engine):
    """Function-scoped so it uses the default event loop (session-scoped async fixtures would need a session-scoped loop)."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except OSError as e:
        pytest.skip(f"Postgres unreachable for integration tests: {e}")


@pytest.fixture
async def db_session(session_factory, _tables) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
