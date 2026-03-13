from abc import ABC, abstractmethod


class IEmbeddingPipeline(ABC):
    """Interface for embedding pipeline operations."""

    @abstractmethod
    async def embed_document(self, document: str) -> tuple[list[list[float]], int]:
        """Embed a document and return the embeddings and the number of chunks."""
        ...
