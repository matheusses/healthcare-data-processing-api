from abc import ABC, abstractmethod


class IEmbeddingPipeline(ABC):
    """Interface for embedding pipeline operations."""

    @abstractmethod
    async def embed_document(self, document: str) -> list[list[float]]:
        """Embed a document and return the embedding."""
        ...
