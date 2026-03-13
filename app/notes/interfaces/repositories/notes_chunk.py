"""Abstract interface for note chunk persistence (content retrieval for context)."""

from abc import abstractmethod
from uuid import UUID


class INoteChunkRepository:
    """Abstract interface for reading note chunks (e.g. for summary/chat context)."""

    @abstractmethod
    async def get_contents_ordered(self, note_id: UUID) -> list[str]:
        """Return chunk content strings for a note, ordered by chunk_index."""
        ...

    @abstractmethod
    async def process(self, note_id: UUID, content: str) -> int:
        """Process a note and its content."""
        ...

    @abstractmethod
    async def delete(self, note_id: UUID) -> None:
        """Delete all chunks for a note."""
        ...
