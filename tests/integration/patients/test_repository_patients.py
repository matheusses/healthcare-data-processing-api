"""Patient repository integration tests (real DB)."""

from uuid import uuid4

import pytest

from app.patients.repository import PatientRepository
from app.shared.schemas.patients import PatientCreateRequest, PatientUpdateRequest


@pytest.mark.asyncio
async def test_patient_repository_crud(db_session):
    repo = PatientRepository(db_session)
    req = PatientCreateRequest(external_id=f"ext-{uuid4()}", full_name="Integration Patient")
    created = await repo.create(req)
    assert created.id is not None
    assert created.external_id == req.external_id

    by_id = await repo.get_by_id(created.id)
    assert by_id is not None
    assert by_id.id == created.id

    updated = await repo.update(created.id, PatientUpdateRequest(full_name="Updated Name"))
    assert updated is not None
    assert updated.full_name == "Updated Name"

    deleted = await repo.delete(created.id)
    assert deleted is True
    assert await repo.get_by_id(created.id) is None
