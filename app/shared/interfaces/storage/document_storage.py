from abc import ABC, abstractmethod

class IDocumentStorage(ABC):
    """Interface for document storage operations."""

    @abstractmethod
    async def upload(self, path: str, raw: bytes) -> str:
        """Upload note content as object; return storage key (object name)."""
        ...

    @abstractmethod
    async def generate_pre_signed_url(self, storage_key: str) -> str:
        """Generate a pre-signed URL for a note content object."""
        ...

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete note content from object storage."""
        ...