from abc import ABC, abstractmethod

class IDocumentExtractor(ABC):
    """Interface for document extractor operations."""

    @abstractmethod
    async def extract_text_from_upload(self, raw: bytes, content_type: str) -> str:
        """Extract text from uploaded note file."""
        ...