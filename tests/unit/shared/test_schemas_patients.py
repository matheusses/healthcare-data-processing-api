"""DTO validation tests for patient schemas."""

import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.shared.schemas.patients import (
    PatientCreateRequest,
    PatientResponse,
    PatientUpdateRequest,
)


def test_patient_create_request_valid():
    data = PatientCreateRequest(
        name="Jane Doe",
        birth_date=date(1990, 1, 15),
        document_number="doc-123",
    )
    assert data.document_number == "doc-123"
    assert data.name == "Jane Doe"
    assert data.birth_date == date(1990, 1, 15)


def test_patient_create_request_empty_name_rejected():
    with pytest.raises(ValidationError):
        PatientCreateRequest(
            name="",
            birth_date=date(1990, 1, 15),
            document_number="doc-123",
        )


def test_patient_create_request_missing_document_number_rejected():
    """document_number is required."""
    with pytest.raises(ValidationError):
        PatientCreateRequest(
            name="Jane Doe",
            birth_date=date(1990, 1, 15),
        )


def test_patient_update_request_optional():
    data = PatientUpdateRequest()
    assert data.name is None
    assert data.birth_date is None
    data2 = PatientUpdateRequest(name="New Name")
    assert data2.name == "New Name"


def test_patient_response_from_attributes():
    uid = uuid.uuid4()
    r = PatientResponse(
        id=uid,
        name="Jane",
        birth_date=date(1990, 1, 15),
        document_number="doc-1",
    )
    assert r.id == uid
    assert r.document_number == "doc-1"
    assert r.name == "Jane"
