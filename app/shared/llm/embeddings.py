"""LangChain chunking, embedding, and write to vector table (pgvector)."""
from __future__ import annotations

from app.shared.interfaces.llm.embeddings import IEmbeddingPipeline
from langchain_openai import OpenAIEmbeddings

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter



logger = logging.getLogger(__name__)






class EmbeddingPipeline(IEmbeddingPipeline):
    """
    Load note content, split into chunks, generate embeddings, write to note_chunks.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int, embedding_model: str, openai_api_key: str) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._embedding = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_api_key,
        )

    async def embed_document(self, document: str) -> list[list[float]]:
        """Embed a document and return the embedding."""
        chunks = self._splitter.split_text(document)
        if not chunks:
            return 0

        embeddings: list[list[float]] = []
        embeddings = await self._embedding.aembed_documents(chunks)
        return embeddings
