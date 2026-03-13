"""APIRouter for /patients; injects Client via Depends(get_patient_client)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from typing import Annotated, Literal

from app.deps import get_patient_client
from app.patients.interfaces.client.patients import IPatientClient
from app.shared.schemas.patients import (
    PatientCreateRequest,
    PatientResponse,
    PatientUpdateRequest,
)

router = APIRouter(prefix="/patients", tags=["patients"])

PatientClientDep = Annotated[IPatientClient, Depends(get_patient_client)]


@router.get("/", response_model=list[PatientResponse])
async def list_patients(
    client: PatientClientDep,
    limit: int = 100,
    offset: int = 0,
    search: str | None = Query(default=None, description="Search by name or document number"),
    order_by: Literal["name", "birth_date", "document_number"] = Query(default="name", description="Order by field"),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="Order direction"),
) -> list[PatientResponse]:
    """List patients with pagination. When search is provided, results are ordered by name similarity (most similar first)."""
    return await client.list_patients(limit=limit, offset=offset, search=search, order_by=order_by, order_direction=order_direction)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: UUID, client: PatientClientDep) -> PatientResponse:
    """Get patient by ID. Returns 404 if not found."""
    return await client.get_by_id(patient_id)


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreateRequest,
    client: PatientClientDep,
) -> PatientResponse:
    """Create a patient. Raises 400 if external_id already exists."""
    return await client.create(body)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    body: PatientUpdateRequest,
    client: PatientClientDep,
) -> PatientResponse:
    """Update a patient. Returns 404 if not found."""
    return await client.update(patient_id, body)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: UUID, client: PatientClientDep) -> None:
    """Delete a patient. Idempotent (204 even if missing)."""
    await client.delete(patient_id)
