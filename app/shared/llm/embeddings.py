"""LangChain chunking, embedding, and write to vector table (pgvector)."""
from __future__ import annotations

from app.config import settings
from app.shared.interfaces.llm.embeddings import IEmbeddingPipeline
from langchain_openai import OpenAIEmbeddings

import logging
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.shared.db.models.note_chunks import NoteChunkModel


logger = logging.getLogger(__name__)






class EmbeddingPipeline(IEmbeddingPipeline):
    """
    Load note content, split into chunks, generate embeddings, write to note_chunks.
    Requires OPENAI_API_KEY to be set for embeddings; otherwise chunks are stored without embeddings.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._embedding = OpenAIEmbeddings(
            model=settings.VECTOR_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

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
        embeddings = await self._embedding.aembed_documents(chunks)

        for i, text in enumerate(chunks):
            embedding = embeddings[i] if i < len(embeddings) else None
            model = NoteChunkModel(
                note_id=note_id,
                content=text,
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
