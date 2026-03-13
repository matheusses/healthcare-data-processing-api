"""NoteService: orchestration, patient validation, repository and optional storage."""

from datetime import datetime
from uuid import UUID


from app.notes.domain import Note
from app.notes.interfaces.repositories.notes import INoteRepository
from app.notes.interfaces.repositories.notes_chunk import INoteChunkRepository
from app.patients.interfaces.client.patients import IPatientClient
from app.shared.exceptions import DomainException, NotFoundException
from app.shared.interfaces.document_loading.extractor import IDocumentExtractor
from app.shared.interfaces.llm.embeddings import IEmbeddingPipeline
from app.shared.interfaces.storage.document_storage import IDocumentStorage
from app.shared.schemas.notes import NoteContentItem, NoteListResponse, NoteResponse


class NoteService:
    """Note business logic; uses note repo, patient repo (for validation), and optional storage."""

    def __init__(
        self,
        note_repository: INoteRepository,
        patient_client: IPatientClient,
        document_storage: IDocumentStorage,
        embedding_pipeline: IEmbeddingPipeline,
        document_extractor: IDocumentExtractor,
        note_chunk_repository: INoteChunkRepository | None = None,
    ) -> None:
        self._note_repository = note_repository
        self._patient_client = patient_client
        self._storage = document_storage
        self._embedding_pipeline = embedding_pipeline
        self._document_extractor = document_extractor
        self._note_chunk_repository = note_chunk_repository

    async def _ensure_patient_exists(self, patient_id: UUID) -> None:
        patient = await self._patient_client.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient not found")

    async def create(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        raw: bytes,
        content_type: str,
    ) -> NoteResponse:
        await self._ensure_patient_exists(patient_id)
        content = await self._document_extractor.extract_text_from_upload(raw, content_type)
        if not content:
            raise DomainException("Failed to extract text from file", code="EXTRACTION_ERROR")
        storage_key = await self._storage.upload(
            path=f"notes/{patient_id}/{recorded_at.isoformat()}.txt", raw=raw
        )
        note = await self._note_repository.create(patient_id, recorded_at, storage_key)
        await self._embedding_pipeline.process_note(note.id, content)
        return self._to_response(note)

    async def list_by_patient(
        self, patient_id: UUID, limit: int = 100, offset: int = 0
    ) -> NoteListResponse:
        await self._ensure_patient_exists(patient_id)
        items = await self._note_repository.list_by_patient(patient_id, limit=limit, offset=offset)
        return NoteListResponse(
            items=[self._to_response(n) for n in items],
            total=len(items),
        )

    async def delete(self, note_id: UUID) -> None:
        note = await self._note_repository.get_by_id(note_id)
        if not note:
            raise NotFoundException("Note not found")
        await self._embedding_pipeline.delete_note_chunks(note_id)
        await self._storage.delete(note.storage_key)
        await self._note_repository.delete(note_id)

    async def generate_pre_signed_url(self, note_id: UUID) -> str:
        note = await self._note_repository.get_by_id(note_id)
        if not note:
            raise NotFoundException("Note not found")
        return await self._storage.generate_pre_signed_url(note.storage_key)

    async def get_note_contents_for_patient(self, patient_id: UUID) -> list[NoteContentItem]:
        """Return full note text per note for a patient (chunks ordered by chunk_index). Reused by summary/chat."""
        await self._ensure_patient_exists(patient_id)
        if not self._note_chunk_repository:
            return []
        notes = await self._note_repository.list_by_patient(patient_id, limit=500, offset=0)
        result: list[NoteContentItem] = []
        for note in notes:
            chunks = await self._note_chunk_repository.get_contents_ordered(note.id)
            result.append(
                NoteContentItem(note_id=note.id, content="\n\n".join(chunks) if chunks else "")
            )
        return result

    def _to_response(self, note: Note) -> NoteResponse:
        return NoteResponse(id=note.id, recorded_at=note.recorded_at)
