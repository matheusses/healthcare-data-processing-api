"""Interface for note client operations."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.shared.schemas.notes import NoteContentItem, NoteListResponse, NoteResponse


class INoteClient(ABC):
    """Interface for note client operations."""

    @abstractmethod
    async def upload(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        raw: bytes,
        content_type: str,
    ) -> NoteResponse:
        """Create a note from a file."""
        ...

    @abstractmethod
    async def list_by_patient(
        self, patient_id: UUID, limit: int = 100, offset: int = 0
    ) -> NoteListResponse:
        """List notes for a patient."""
        ...

    @abstractmethod
    async def generate_pre_signed_url(self, note_id: UUID) -> str:
        """Generate a pre-signed URL for a note content object."""
        ...

    @abstractmethod
    async def delete(self, note_id: UUID) -> None:
        """Delete note. Raises NotFoundException if not found."""
        ...

    @abstractmethod
    async def get_note_contents_for_patient(self, patient_id: UUID) -> list[NoteContentItem]:
        """Return full note text per note for a patient (for summary/chat context)."""
        ...
