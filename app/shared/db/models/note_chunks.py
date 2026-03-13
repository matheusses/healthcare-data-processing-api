"""ORM model for note_chunks table (vector store)."""

from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.shared.db.database import Base


class NoteChunkModel(Base):
    """Chunk of a note with embedding for vector similarity search."""

    __tablename__ = "note_chunks"

    id: Mapped[object] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    note_id: Mapped[object] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.VECTOR_EMBEDDING_DIMENSIONS),
        nullable=True,
    )
    chunk_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
