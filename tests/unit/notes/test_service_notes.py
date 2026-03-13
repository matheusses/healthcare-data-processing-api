"""NoteService tests with mocked repository and storage."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.notes.domain import Note
from app.notes.service import NoteService
from app.patients.domain import Patient
from app.shared.exceptions import NotFoundException


class MockNoteRepository:
    def __init__(self):
        self.by_id = {}
        self.by_patient = {}

    async def get_by_id(self, id):
        return self.by_id.get(id)

    async def create(self, patient_id, recorded_at, storage_key: str):
        note = Note(
            id=uuid4(),
            patient_id=patient_id,
            recorded_at=recorded_at,
            storage_key=storage_key,
        )
        self.by_id[note.id] = note
        self.by_patient.setdefault(patient_id, []).append(note)
        return note

    async def delete(self, id):
        if id in self.by_id:
            note = self.by_id[id]
            del self.by_id[id]
            if note.patient_id in self.by_patient:
                self.by_patient[note.patient_id] = [
                    n for n in self.by_patient[note.patient_id] if n.id != id
                ]
            return True
        return False

    async def list_by_patient(self, patient_id, limit=100, offset=0):
        notes = self.by_patient.get(patient_id, [])
        notes_sorted = sorted(notes, key=lambda n: n.recorded_at, reverse=True)
        return notes_sorted[offset : offset + limit]


class MockPatientClient:
    def __init__(self, existing_ids=None):
        self.existing_ids = set(existing_ids or [])

    async def get_by_id(self, id):
        if id in self.existing_ids:
            return Patient(
                id=id,
                name="Test",
                birth_date=datetime(1990, 1, 1).date(),
                document_number="doc-1",
            )
        return None


class MockDocumentStorage:
    async def upload(self, path, raw):
        return path or "notes/mock/key.txt"

    async def delete(self, storage_key):
        pass

    async def generate_pre_signed_url(self, storage_key):
        return f"https://example.com/{storage_key}"


class MockDocumentExtractor:
    async def extract_text_from_upload(self, raw: bytes, content_type: str) -> str:
        return "SOAP note content"


class MockNoteChunkRepository:
    async def process(self, note_id, content: str) -> int:
        return 1

    async def delete(self, note_id) -> None:
        pass

    async def get_contents_ordered(self, note_id) -> list:
        return []


@pytest.mark.asyncio
async def test_note_service_create_ok():
    patient_id = uuid4()
    note_repo = MockNoteRepository()
    patient_client = MockPatientClient(existing_ids=[patient_id])
    storage = MockDocumentStorage()
    extractor = MockDocumentExtractor()
    note_chunk_repo = MockNoteChunkRepository()
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_client,
        document_storage=storage,
        document_extractor=extractor,
        note_chunk_repository=note_chunk_repo,
    )
    rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    resp = await svc.create(
        patient_id=patient_id,
        recorded_at=rec,
        raw=b"file content",
        content_type="text/plain",
    )
    assert resp.id is not None
    assert resp.recorded_at == rec


@pytest.mark.asyncio
async def test_note_service_create_patient_not_found():
    patient_id = uuid4()
    note_repo = MockNoteRepository()
    patient_client = MockPatientClient(existing_ids=[])
    storage = MockDocumentStorage()
    extractor = MockDocumentExtractor()
    note_chunk_repo = MockNoteChunkRepository()
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_client,
        document_storage=storage,
        document_extractor=extractor,
        note_chunk_repository=note_chunk_repo,
    )
    rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(NotFoundException) as exc_info:
        await svc.create(
            patient_id=patient_id,
            recorded_at=rec,
            raw=b"SOAP note",
            content_type="text/plain",
        )
    assert "Patient not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_note_service_delete_not_found():
    note_repo = MockNoteRepository()
    patient_client = MockPatientClient(existing_ids=[])
    storage = MockDocumentStorage()
    note_chunk_repo = MockNoteChunkRepository()
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_client,
        document_storage=storage,
        document_extractor=MockDocumentExtractor(),
        note_chunk_repository=note_chunk_repo,
    )
    with pytest.raises(NotFoundException):
        await svc.delete(uuid4())


@pytest.mark.asyncio
async def test_note_service_list_by_patient():
    patient_id = uuid4()
    note_repo = MockNoteRepository()
    rec1 = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    rec2 = datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
    await note_repo.create(patient_id, rec1, "key1.txt")
    await note_repo.create(patient_id, rec2, "key2.txt")
    patient_client = MockPatientClient(existing_ids=[patient_id])
    storage = MockDocumentStorage()
    note_chunk_repo = MockNoteChunkRepository()
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_client,
        document_storage=storage,
        document_extractor=MockDocumentExtractor(),
        note_chunk_repository=note_chunk_repo,
    )
    out = await svc.list_by_patient(patient_id, limit=10, offset=0)
    assert out.total == 2
    assert len(out.items) == 2
