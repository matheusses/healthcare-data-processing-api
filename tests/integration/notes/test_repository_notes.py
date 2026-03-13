"""Note repository integration tests (real DB)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.notes.repository import NoteRepository
from app.patients.repository import PatientRepository
from app.shared.schemas.patients import PatientCreateRequest


@pytest.mark.asyncio
async def test_note_repository_crud(db_session):
    """Create patient, then create/list/delete notes."""
    patient_repo = PatientRepository(db_session)
    patient_req = PatientCreateRequest(
        name="Notes Test Patient",
        birth_date=datetime(1990, 1, 1).date(),
        document_number=f"doc-notes-{uuid4()}",
    )
    patient = await patient_repo.create(patient_req)
    assert patient.id is not None

    note_repo = NoteRepository(db_session)
    rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    storage_key = "patients/1/notes/1.txt"
    note = await note_repo.create(
        patient_id=patient.id,
        recorded_at=rec,
        storage_key=storage_key,
    )
    assert note.id is not None
    assert note.patient_id == patient.id
    assert note.storage_key == storage_key

    by_id = await note_repo.get_by_id(note.id)
    assert by_id is not None
    assert by_id.id == note.id

    notes_list = await note_repo.list_by_patient(patient.id, limit=10, offset=0)
    assert len(notes_list) == 1

    deleted = await note_repo.delete(note.id)
    assert deleted is True
    assert await note_repo.get_by_id(note.id) is None
