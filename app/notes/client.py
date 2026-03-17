"""Public facade for notes; deps injected via parameter. Used by router."""

from datetime import datetime
from uuid import UUID

from app.notes.interfaces.client.notes import INoteClient
from app.notes.service import NoteService
from app.shared.schemas.notes import NoteContentItem, NoteListResponse, NoteResponse


class NoteClient(INoteClient):
    """Facade for note operations; receives service via parameter."""

    def __init__(self, note_service: NoteService) -> None:
        self._service = note_service

    async def upload(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        raw: bytes,
        content_type: str,
    ) -> NoteResponse:
        return await self._service.create(
            patient_id=patient_id,
            recorded_at=recorded_at,
            raw=raw,
            content_type=content_type,
        )

    async def list_by_patient(
        self, patient_id: UUID, limit: int = 100, offset: int = 0
    ) -> NoteListResponse:
        return await self._service.list_by_patient(patient_id, limit=limit, offset=offset)

    async def generate_pre_signed_url(self, note_id: UUID) -> str:
        return await self._service.generate_pre_signed_url(note_id)

    async def delete(self, note_id: UUID) -> None:
        await self._service.delete(note_id)

    async def get_note_contents_for_patient(
        self, patient_id: UUID, query: str
    ) -> list[NoteContentItem]:
        return await self._service.get_note_contents_for_patient(patient_id, query)
