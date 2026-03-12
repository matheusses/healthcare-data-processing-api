"""Async SQLAlchemy engine and request-scoped session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings


class Base(DeclarativeBase):
    """Declarative base for ORM models."""

    pass


def build_engine(settings: Settings):
    """Create async engine with connection pooling."""
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=settings.environment == "development",
    )


def build_session_factory(engine):
    """Create async session factory."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_from_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped DB session given a session factory (e.g. from container)."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
