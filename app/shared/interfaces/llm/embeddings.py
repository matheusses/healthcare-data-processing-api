from abc import ABC, abstractmethod
from uuid import UUID

class IEmbeddingPipeline(ABC):
    """Interface for embedding pipeline operations."""

    @abstractmethod
    async def process_note(self, note_id: UUID, content: str) -> int:
        """Split content into chunks, optionally embed, persist to note_chunks. Returns number of chunks written."""
        ...

    @abstractmethod
    async def delete_note_chunks(self, note_id: UUID) -> None:
        """Delete all chunks for a note."""
        ...