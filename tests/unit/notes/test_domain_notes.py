"""Note domain entity tests."""

import uuid
from datetime import datetime, timezone

from app.notes.domain import Note


def test_note_from_attributes():
    uid = uuid.uuid4()
    patient_id = uuid.uuid4()
    rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    note = Note(
        id=uid,
        patient_id=patient_id,
        recorded_at=rec,
        storage_key="patients/1/notes/2.txt",
    )
    assert note.id == uid
    assert note.patient_id == patient_id
    assert note.storage_key == "patients/1/notes/2.txt"
