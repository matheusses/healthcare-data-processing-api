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
    recorded_at: datetime

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """Response DTO for list of notes."""

    items: list[NoteResponse]
    total: int


class NoteContentItem(BaseModel):
    """Full text of a single note (from chunks), for summary/chat context."""

    note_id: UUID
    content: str = Field("", description="Full note text from chunks ordered by chunk index")
