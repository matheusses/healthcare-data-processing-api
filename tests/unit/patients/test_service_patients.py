"""PatientService tests with mocked repository."""

from datetime import date
from uuid import uuid4

import pytest

from app.patients.domain import Patient
from app.patients.service import PatientService
from app.shared.exceptions import DomainException, NotFoundException
from app.shared.schemas.patients import (
    PatientCreateRequest,
    PatientUpdateRequest,
)


class MockPatientRepository:
    def __init__(self):
        self.by_id = {}
        self.by_document_number = {}

    async def get_by_id(self, id):
        return self.by_id.get(id)

    async def get_by_document_number(self, document_number):
        return self.by_document_number.get(document_number)

    async def create(self, data):
        patient = Patient(
            id=uuid4(),
            name=data.name,
            birth_date=data.birth_date,
            document_number=data.document_number,
        )
        self.by_document_number[data.document_number] = patient
        self.by_id[patient.id] = patient
        return patient

    async def update(self, id, data):
        if id not in self.by_id:
            return None
        patient = self.by_id[id]
        if data.name is not None or data.birth_date is not None:
            patient = Patient(
                id=patient.id,
                name=data.name if data.name is not None else patient.name,
                birth_date=data.birth_date if data.birth_date is not None else patient.birth_date,
                document_number=patient.document_number,
            )
            self.by_id[id] = patient
        return patient

    async def delete(self, id):
        if id in self.by_id:
            patient = self.by_id[id]
            del self.by_id[id]
            if patient.document_number in self.by_document_number:
                del self.by_document_number[patient.document_number]
            return True
        return False

    async def list_patients(
        self, limit=100, offset=0, search=None, order_by="name", order_direction="asc"
    ):
        items = list(self.by_id.values())[offset : offset + limit]
        return items


@pytest.mark.asyncio
async def test_patient_service_create_ok():
    repo = MockPatientRepository()
    svc = PatientService(patient_repository=repo)
    req = PatientCreateRequest(name="Jane", birth_date=date(1990, 1, 15), document_number="doc-1")
    resp = await svc.create(req)
    assert resp.document_number == "doc-1"
    assert resp.name == "Jane"
    assert resp.id is not None


@pytest.mark.asyncio
async def test_patient_service_create_duplicate_raises():
    repo = MockPatientRepository()
    await repo.create(
        PatientCreateRequest(name="Jane", birth_date=date(1990, 1, 15), document_number="doc-1")
    )
    svc = PatientService(patient_repository=repo)
    with pytest.raises(DomainException) as exc_info:
        await svc.create(
            PatientCreateRequest(name="Other", birth_date=date(1985, 5, 1), document_number="doc-1")
        )
    assert exc_info.value.code == "DUPLICATE_DOCUMENT_NUMBER"


@pytest.mark.asyncio
async def test_patient_service_get_by_id_not_found():
    repo = MockPatientRepository()
    svc = PatientService(patient_repository=repo)
    with pytest.raises(NotFoundException):
        await svc.get_by_id(uuid4())


@pytest.mark.asyncio
async def test_patient_service_update_not_found():
    repo = MockPatientRepository()
    svc = PatientService(patient_repository=repo)
    out = await svc.update(uuid4(), PatientUpdateRequest(name="X"))
    assert out is None


@pytest.mark.asyncio
async def test_patient_service_list_patients_returns_response_dtos():
    repo = MockPatientRepository()
    await repo.create(
        PatientCreateRequest(name="Jane Doe", birth_date=date(1990, 1, 1), document_number="doc-1")
    )
    await repo.create(
        PatientCreateRequest(name="John Doe", birth_date=date(1985, 6, 1), document_number="doc-2")
    )
    svc = PatientService(patient_repository=repo)
    out = await svc.list_patients(limit=10, offset=0)
    assert len(out) == 2
    assert all(hasattr(p, "name") and hasattr(p, "id") for p in out)
    assert {p.document_number for p in out} == {"doc-1", "doc-2"}
