"""LangChain chunking, embedding, and write to vector table (pgvector)."""

from __future__ import annotations

import logging
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.shared.db.models.note_chunks import NoteChunkModel

logger = logging.getLogger(__name__)

# Default chunk size/overlap for SOAP-style notes
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


class EmbeddingPipeline:
    """
    Load note content, split into chunks, generate embeddings, write to note_chunks.
    Requires OPENAI_API_KEY to be set for embeddings; otherwise chunks are stored without embeddings.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._embedding = None
        if settings.openai_api_key:
            try:
                from langchain_openai import OpenAIEmbeddings

                self._embedding = OpenAIEmbeddings(
                    model=settings.vector_embedding_model,
                    openai_api_key=settings.openai_api_key,
                )
            except Exception as e:
                logger.warning("OpenAI embeddings not available: %s", e)

    def is_available(self) -> bool:
        """True if embedding provider is configured."""
        return self._embedding is not None

    async def process_note(
        self,
        session: AsyncSession,
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
        if self._embedding:
            try:
                embeddings = await self._embedding.aembed_documents(chunks)
            except Exception as e:
                logger.warning("Embedding failed, storing chunks without embeddings: %s", e)

        for i, text in enumerate(chunks):
            embedding = embeddings[i] if i < len(embeddings) else None
            model = NoteChunkModel(
                note_id=note_id,
                content=text,
                embedding=embedding,
                chunk_metadata={"chunk_index": i, "total_chunks": len(chunks)},
            )
            session.add(model)
        await session.flush()
        return len(chunks)

    async def delete_chunks_for_note(self, session: AsyncSession, note_id: UUID) -> int:
        """Delete all chunks for a note (e.g. when note is deleted). Returns count deleted."""
        from sqlalchemy import delete

        stmt = delete(NoteChunkModel).where(NoteChunkModel.note_id == note_id)
        result = await session.execute(stmt)
        return result.rowcount or 0
