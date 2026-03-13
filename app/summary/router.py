"""APIRouter for GET /patients/{patient_id}/summary."""

from uuid import UUID

from fastapi import APIRouter, Depends
from typing import Annotated

from app.core.deps import get_summary_client
from app.shared.schemas.summary import PatientSummaryResponse
from app.summary.interfaces.client.summary import ISummaryClient

router = APIRouter(prefix="/patients", tags=["summary"])

SummaryClientDep = Annotated[ISummaryClient, Depends(get_summary_client)]


@router.get("/{patient_id}/summary", response_model=PatientSummaryResponse)
async def get_patient_summary(patient_id: UUID, client: SummaryClientDep) -> PatientSummaryResponse:
    """Return SOAP summary for the patient. Returns 404 if patient not found."""
    return await client.get_summary(patient_id)
