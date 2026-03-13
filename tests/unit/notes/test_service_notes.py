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

    async def create(self, patient_id, recorded_at, content, storage_key=None):
        note = Note(
            id=uuid4(),
            patient_id=patient_id,
            recorded_at=recorded_at,
            content=content,
            storage_key=storage_key,
            created_at=recorded_at,
        )
        self.by_id[note.id] = note
        self.by_patient.setdefault(patient_id, []).append(note)
        return note

    async def update_storage_key(self, id, storage_key):
        if id in self.by_id:
            note = self.by_id[id]
            self.by_id[id] = Note(
                id=note.id,
                patient_id=note.patient_id,
                recorded_at=note.recorded_at,
                content=note.content,
                storage_key=storage_key,
                created_at=note.created_at,
            )
            return self.by_id[id]
        return None

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

    async def count_by_patient(self, patient_id):
        return len(self.by_patient.get(patient_id, []))


class MockPatientRepository:
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


@pytest.mark.asyncio
async def test_note_service_create_ok():
    patient_id = uuid4()
    note_repo = MockNoteRepository()
    patient_repo = MockPatientRepository(existing_ids=[patient_id])
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_repo,
        document_storage=None,
    )
    rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    resp = await svc.create(
        patient_id=patient_id,
        recorded_at=rec,
        content="SOAP note content",
        store_in_object_storage=False,
    )
    assert resp.patient_id == patient_id
    assert resp.content == "SOAP note content"
    assert resp.id is not None


@pytest.mark.asyncio
async def test_note_service_create_patient_not_found():
    patient_id = uuid4()
    note_repo = MockNoteRepository()
    patient_repo = MockPatientRepository(existing_ids=[])  # no patients
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_repo,
        document_storage=None,
    )
    rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(NotFoundException) as exc_info:
        await svc.create(
            patient_id=patient_id,
            recorded_at=rec,
            content="SOAP note",
            store_in_object_storage=False,
        )
    assert "Patient not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_note_service_get_by_id_not_found():
    note_repo = MockNoteRepository()
    patient_repo = MockPatientRepository(existing_ids=[])
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_repo,
        document_storage=None,
    )
    with pytest.raises(NotFoundException):
        await svc.get_by_id(uuid4())


@pytest.mark.asyncio
async def test_note_service_list_by_patient():
    patient_id = uuid4()
    note_repo = MockNoteRepository()
    await note_repo.create(
        patient_id,
        datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
        "Note 1",
        None,
    )
    await note_repo.create(
        patient_id,
        datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc),
        "Note 2",
        None,
    )
    patient_repo = MockPatientRepository(existing_ids=[patient_id])
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_repo,
        document_storage=None,
    )
    out = await svc.list_by_patient(patient_id, limit=10, offset=0)
    assert out.total == 2
    assert len(out.items) == 2


@pytest.mark.asyncio
async def test_note_service_delete_not_found():
    note_repo = MockNoteRepository()
    patient_repo = MockPatientRepository(existing_ids=[])
    svc = NoteService(
        note_repository=note_repo,
        patient_client=patient_repo,
        document_storage=None,
    )
    with pytest.raises(NotFoundException):
        await svc.delete(uuid4())
