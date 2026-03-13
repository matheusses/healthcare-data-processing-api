"""Patient request/response/internal DTOs."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class PatientCreateRequest(BaseModel):
    """Request DTO for creating a patient."""

    name: str = Field(..., min_length=1, max_length=500, description="Patient's name")
    birth_date: date = Field(..., description="Patient's birth date")
    document_number: str = Field(..., max_length=50, description="Patient's document number")


class PatientUpdateRequest(BaseModel):
    """Request DTO for updating a patient."""

    name: str | None = Field(None, min_length=1, max_length=500, description="Patient's name")
    birth_date: date | None = Field(None, description="Patient's birth date")


class PatientResponse(BaseModel):
    """Response DTO for patient."""

    id: UUID
    name: str
    birth_date: date
    document_number: str

    model_config = {"from_attributes": True}
