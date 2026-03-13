"""NoteChunkRepository: read note chunks ordered by chunk_index for context assembly."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.interfaces.repositories.notes_chunk import INoteChunkRepository
from app.shared.db.models.note_chunks import NoteChunkModel


class NoteChunkRepository(INoteChunkRepository):
    """Read chunks for a note ordered by chunk_metadata->chunk_index."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_contents_ordered(self, note_id: UUID) -> list[str]:
        """Return chunk content strings for a note, ordered by chunk_index."""
        stmt = (
            select(NoteChunkModel.content)
            .where(NoteChunkModel.note_id == note_id)
            .order_by(text("(chunk_metadata->>'chunk_index')::int nulls last"))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
