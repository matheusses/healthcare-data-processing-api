"""APIRouter for POST /patients/{patient_id}/chat."""

from uuid import UUID

from fastapi import APIRouter, Depends
from typing import Annotated

from app.deps import get_chat_client
from app.shared.schemas.chat import ChatRequest, ChatResponse
from app.chat.interfaces.client.chat import IChatClient

router = APIRouter(prefix="/patients", tags=["chat"])

ChatClientDep = Annotated[IChatClient, Depends(get_chat_client)]


@router.post("/{patient_id}/chat", response_model=ChatResponse)
async def post_patient_chat(
    patient_id: UUID,
    body: ChatRequest,
    client: ChatClientDep,
) -> ChatResponse:
    """Answer a question about the patient. Returns 404 if patient not found."""
    return await client.send(patient_id, body.message)
