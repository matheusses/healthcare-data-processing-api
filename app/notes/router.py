"""APIRouter for /patients/{patient_id}/notes; upload, list, delete."""

from datetime import datetime, timezone
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.deps import get_note_client
from app.notes.interfaces.client.notes import INoteClient
from app.shared.schemas.notes import NoteListResponse, NoteResponse
from app.config import settings

router = APIRouter(prefix="/patients/{patient_id}/notes", tags=["notes"])

NoteClientDep = Annotated[INoteClient, Depends(get_note_client)]

# Max file size for upload (10 MB) to avoid DoS
UPLOAD_MAX_BYTES = 10 * 1024 * 1024


@router.post("/upload", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def upload_note_file(
    patient_id: UUID,
    client: NoteClientDep,
    file: Annotated[
        UploadFile,
        File(
            description="Note content: .txt, .pdf, or handwritten image (.jpg, .png)",
            content_type=settings.allowed_content_types_list,
        ),
    ],
    recorded_at: Annotated[
        datetime | None,
        Form(description="When the note was recorded (ISO datetime). Omit to use current time."),
    ] = None,
) -> NoteResponse:
    effective_recorded_at = recorded_at or datetime.now(timezone.utc)
    raw = await file.read()

    return await client.upload(
        patient_id=patient_id,
        recorded_at=effective_recorded_at,
        raw=raw,
        content_type=file.content_type,
    )


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    patient_id: UUID,
    client: NoteClientDep,
    limit: int = 100,
    offset: int = 0,
) -> NoteListResponse:
    """List all notes for a patient."""
    return await client.list_by_patient(patient_id, limit=limit, offset=offset)


@router.get("/{note_id}/pre-signed-url", response_model=str)
async def generate_pre_signed_url(note_id: UUID, client: NoteClientDep) -> str:
    """Generate a pre-signed URL for a note content object."""
    return await client.generate_pre_signed_url(note_id)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: UUID, client: NoteClientDep) -> None:
    await client.delete(note_id)
