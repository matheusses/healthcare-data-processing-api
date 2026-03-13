"""NoteChunkRepository: read note chunks ordered by chunk_index for context assembly."""

from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.interfaces.repositories.notes_chunk import INoteChunkRepository
from app.shared.db.models.note_chunks import NoteChunkModel
from app.shared.interfaces.llm.embeddings import IEmbeddingPipeline


class NoteChunkRepository(INoteChunkRepository):
    """Read chunks for a note ordered by chunk_metadata->chunk_index."""

    def __init__(self, session: AsyncSession, embedding_pipeline: IEmbeddingPipeline) -> None:
        self._session = session
        self._embedding_pipeline = embedding_pipeline
         
    async def get_contents_ordered(self, note_id: UUID) -> list[str]:
        """Return chunk content strings for a note, ordered by chunk_index."""
        stmt = (
            select(NoteChunkModel.content)
            .where(NoteChunkModel.note_id == note_id)
            .order_by(text("(chunk_metadata->>'chunk_index')::int nulls last"))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def process_note(
        self,
        note_id: UUID,
        content: str,
    ) -> int:
        """
        Split content into chunks, optionally embed, persist to note_chunks.
        Returns number of chunks written.
        """
        chunks = self._splitter.split_text(content)
        if not chunks:
            return 0

        embeddings: list[list[float]] = []
        embeddings = await self._embedding_pipeline.embed_documents(chunks)

        for i, content in enumerate(chunks):
            embedding = embeddings[i] if i < len(embeddings) else None
            model = NoteChunkModel(
                note_id=note_id,
                content=content,
                embedding=embedding,
                chunk_metadata={"chunk_index": i, "total_chunks": len(chunks)},
            )
            self._session.add(model)
        await self._session.flush()
        return len(chunks)

    async def delete_note_chunks(self, note_id: UUID) -> None:
        """Delete all chunks for a note."""
        stmt = delete(NoteChunkModel).where(NoteChunkModel.note_id == note_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True
