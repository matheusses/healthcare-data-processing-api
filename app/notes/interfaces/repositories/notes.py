"""Abstract interface for note persistence."""

from abc import abstractmethod
from datetime import datetime
from uuid import UUID

from app.notes.domain import Note


class INoteRepository:
    """Abstract interface for note persistence."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Note | None:
        """Return note by id or None."""
        ...

    @abstractmethod
    async def create(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        storage_key: str,
    ) -> Note:
        """Create note and return domain entity."""
        ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete note; return True if deleted."""
        ...

    @abstractmethod
    async def list_by_patient(
        self, patient_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Note]:
        """List notes for a patient ordered by recorded_at desc."""
        ...
