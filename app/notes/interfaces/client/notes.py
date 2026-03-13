"""Interface for note client operations."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.shared.schemas.notes import NoteCreateRequest, NoteListResponse, NoteResponse


class INoteClient(ABC):
    """Interface for note client operations."""

    @abstractmethod
    async def upload(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        content: str,
        store_in_object_storage: bool = False,
    ) -> NoteResponse:
        """Create a note (body content). Optionally store raw content in object storage."""
        ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID, limit: int = 100, offset: int = 0) -> NoteListResponse:
        """List notes for a patient."""
        ...

    @abstractmethod
    async def get_by_id(self, note_id: UUID) -> NoteResponse:
        """Get note by id. Raises NotFoundException if not found."""
        ...

    @abstractmethod
    async def delete(self, note_id: UUID) -> None:
        """Delete note. Raises NotFoundException if not found."""
        ...
