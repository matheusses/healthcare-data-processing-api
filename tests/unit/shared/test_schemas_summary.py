"""DTO validation tests for summary schemas."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.shared.schemas.summary import PatientHeading, PatientSummaryResponse


def test_patient_heading_valid():
    h = PatientHeading(name="Jane Doe", age=34, document_number="doc-123")
    assert h.name == "Jane Doe"
    assert h.age == 34
    assert h.document_number == "doc-123"


def test_patient_heading_missing_field_rejected():
    with pytest.raises(ValidationError):
        PatientHeading(name="Jane", age=34)


def test_patient_summary_response_valid():
    h = PatientHeading(name="Jane", age=30, document_number="d1")
    gen = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    nid = uuid.uuid4()
    r = PatientSummaryResponse(
        patient_heading=h,
        subjective="Pt reports headache.",
        objective="BP 120/80.",
        assessment="Benign.",
        plan="Follow up PRN.",
        generated_at=gen,
        note_ids=[nid],
    )
    assert r.patient_heading.name == "Jane"
    assert r.subjective == "Pt reports headache."
    assert r.note_ids == [nid]
    assert r.generated_at == gen


def test_patient_summary_response_defaults():
    h = PatientHeading(name="A", age=0, document_number="x")
    r = PatientSummaryResponse(patient_heading=h, generated_at=datetime.now(timezone.utc))
    assert r.subjective == ""
    assert r.objective == ""
    assert r.assessment == ""
    assert r.plan == ""
    assert r.note_ids == []
