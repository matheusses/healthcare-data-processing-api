"""NoteService: orchestration, patient validation, repository and optional storage."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.domain import Note
from app.notes.interfaces.repositories.notes import INoteRepository
from app.patients.interfaces.client.patients import IPatientClient
from app.shared.exceptions import NotFoundException
from app.shared.llm.embeddings import EmbeddingPipeline
from app.shared.schemas.notes import NoteListResponse, NoteResponse
from app.shared.storage.document_storage import DocumentStorageClient


class NoteService:
    """Note business logic; uses note repo, patient repo (for validation), and optional storage."""

    def __init__(
        self,
        note_repository: INoteRepository,
        patient_client: IPatientClient,
        document_storage: DocumentStorageClient | None = None,
        embedding_pipeline: EmbeddingPipeline | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._repo = note_repository
        self._patient_client = patient_client
        self._storage = document_storage
        self._embedding_pipeline = embedding_pipeline
        self._session = session

    async def _ensure_patient_exists(self, patient_id: UUID) -> None:
        patient = await self._patient_client.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient not found")

    async def create(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        content: str,
        store_in_object_storage: bool = False,
    ) -> NoteResponse:
        await self._ensure_patient_exists(patient_id)
        note = await self._repo.create(
            patient_id=patient_id,
            recorded_at=recorded_at,
            content=content,
            storage_key=None,
        )
        if store_in_object_storage and self._storage:
            try:
                storage_key = self._storage.upload_note_content(patient_id, note.id, content)
                note = await self._repo.update_storage_key(note.id, storage_key) or note
            except Exception:
                await self._repo.delete(note.id)
                raise
        if self._embedding_pipeline and self._embedding_pipeline.is_available() and self._session:
            try:
                await self._embedding_pipeline.process_note(self._session, note.id, content)
            except Exception:
                pass
        return self._to_response(note)

    async def get_by_id(self, note_id: UUID) -> NoteResponse:
        note = await self._repo.get_by_id(note_id)
        if not note:
            raise NotFoundException("Note not found")
        return self._to_response(note)

    async def list_by_patient(self, patient_id: UUID, limit: int = 100, offset: int = 0) -> NoteListResponse:
        await self._ensure_patient_exists(patient_id)
        items = await self._repo.list_by_patient(patient_id, limit=limit, offset=offset)
        total = await self._repo.count_by_patient(patient_id)
        return NoteListResponse(
            items=[self._to_response(n) for n in items],
            total=total,
        )

    async def delete(self, note_id: UUID) -> None:
        note = await self._repo.get_by_id(note_id)
        if not note:
            raise NotFoundException("Note not found")
        if self._embedding_pipeline and self._session:
            try:
                await self._embedding_pipeline.delete_chunks_for_note(self._session, note_id)
            except Exception:
                pass
        if note.storage_key and self._storage:
            self._storage.delete_object(note.storage_key)
        deleted = await self._repo.delete(note_id)
        if not deleted:
            raise NotFoundException("Note not found")

    def _to_response(self, note: Note) -> NoteResponse:
        return NoteResponse(
            id=note.id,
            patient_id=note.patient_id,
            recorded_at=note.recorded_at,
            content=note.content,
            storage_key=note.storage_key,
            created_at=note.created_at,
        )
