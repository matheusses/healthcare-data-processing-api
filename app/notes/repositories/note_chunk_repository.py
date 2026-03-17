"""NoteChunkRepository: read note chunks ordered by chunk_index for context assembly."""

from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.interfaces.repositories.notes_chunk import INoteChunkRepository
from app.shared.db.models.note_chunks import NoteChunkModel
from app.shared.interfaces.llm.embeddings import IEmbeddingPipeline
from app.config import settings


class NoteChunkRepository(INoteChunkRepository):
    """Read chunks for a note ordered by chunk_metadata->chunk_index."""

    def __init__(self, session: AsyncSession, embedding_pipeline: IEmbeddingPipeline) -> None:
        self._session = session
        self._embedding_pipeline = embedding_pipeline

    async def get_contents_ordered(self, note_id: UUID, content: str) -> list[str]:
        """Return chunk content strings for a note, ordered by chunk_index."""
        query_embedding = await self._embedding_pipeline.embed_query(content)
        stmt = (
            select(NoteChunkModel.content)
            .where(NoteChunkModel.note_id == note_id)
            .where(
                NoteChunkModel.embedding.cosine_distance(query_embedding)
                < (1.0 - settings.PG_TRGM_SIMILARITY_THRESHOLD)
            )
            .order_by(text("(chunk_metadata->>'chunk_index')::int nulls last"))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def process(
        self,
        note_id: UUID,
        content: str,
    ) -> int:
        """Process a note and its content."""

        embeddings: list[list[float]] = []
        embeddings, chunks = await self._embedding_pipeline.embed_document(content)

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

    async def delete(self, note_id: UUID) -> None:
        """Delete all chunks for a note."""
        stmt = delete(NoteChunkModel).where(NoteChunkModel.note_id == note_id)
        await self._session.execute(stmt)
        await self._session.flush()
