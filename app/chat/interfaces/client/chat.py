"""Interface for chat client."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.shared.schemas.chat import ChatResponse


class IChatClient(ABC):
    """Interface for patient chat (Q&A) operations."""

    @abstractmethod
    async def send(self, patient_id: UUID, message: str) -> ChatResponse:
        """Answer a question about the patient. Raises NotFoundException if patient not found."""
        ...
