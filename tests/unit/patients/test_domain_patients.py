"""Patient domain entity tests."""

from datetime import date
from uuid import uuid4

from app.patients.domain import Patient
from app.shared.schemas.patients import PatientCreateRequest


def test_patient_from_request_data():
    """Patient can be built from request-like data (domain entity shape)."""
    data = PatientCreateRequest(
        name="Jane Doe",
        birth_date=date(1990, 1, 15),
        document_number="doc-1",
    )
    p = Patient(
        id=uuid4(),
        name=data.name,
        birth_date=data.birth_date,
        document_number=data.document_number,
    )
    assert p.document_number == "doc-1"
    assert p.name == "Jane Doe"
    assert p.id is not None
