"""Public facade for notes; deps injected via parameter. Used by router."""

from datetime import datetime
from uuid import UUID

from app.notes.interfaces.client.notes import INoteClient
from app.notes.service import NoteService
from app.shared.schemas.notes import NoteListResponse, NoteResponse


class NoteClient(INoteClient):
    """Facade for note operations; receives service via parameter."""

    def __init__(self, note_service: NoteService) -> None:
        if not isinstance(note_service, NoteService):
            raise TypeError("note_service must be NoteService")
        self._service = note_service

    async def upload(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        content: str,
        store_in_object_storage: bool = False,
    ) -> NoteResponse:
        return await self._service.create(
            patient_id=patient_id,
            recorded_at=recorded_at,
            content=content,
            store_in_object_storage=store_in_object_storage,
        )

    async def list_by_patient(self, patient_id: UUID, limit: int = 100, offset: int = 0) -> NoteListResponse:
        return await self._service.list_by_patient(patient_id, limit=limit, offset=offset)

    async def get_by_id(self, note_id: UUID) -> NoteResponse:
        return await self._service.get_by_id(note_id)

    async def delete(self, note_id: UUID) -> None:
        await self._service.delete(note_id)
