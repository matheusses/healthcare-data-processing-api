"""Request/response DTOs for patient chat (Q&A over patient context)."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /patients/{id}/chat."""

    message: str = Field(
        ..., min_length=1, max_length=16_384, description="User question about the patient"
    )


class ChatResponse(BaseModel):
    """Response for POST /patients/{id}/chat."""

    response: str = Field(..., description="LLM answer based on patient context")
