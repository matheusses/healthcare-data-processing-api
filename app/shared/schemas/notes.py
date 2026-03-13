"""Note request/response DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NoteCreateRequest(BaseModel):
    """Request DTO for creating a note (body with content + recorded_at)."""

    recorded_at: datetime = Field(..., description="When the note was recorded (encounter date)")
    content: str = Field(..., min_length=1, max_length=100_000, description="Note text (e.g. SOAP)")


class NoteResponse(BaseModel):
    """Response DTO for a single note."""

    id: UUID
    patient_id: UUID
    recorded_at: datetime
    content: str
    storage_key: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """Response DTO for list of notes."""

    items: list[NoteResponse]
    total: int
