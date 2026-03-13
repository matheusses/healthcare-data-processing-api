"""APIRouter for /patients/{patient_id}/notes; upload, list, delete."""

from datetime import datetime
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.deps import get_note_client
from app.notes.interfaces.client.notes import INoteClient
from app.shared.schemas.notes import NoteCreateRequest, NoteListResponse, NoteResponse

router = APIRouter(prefix="/patients/{patient_id}/notes", tags=["notes"])

NoteClientDep = Annotated[INoteClient, Depends(get_note_client)]


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def upload_note_body(patient_id: UUID, client: NoteClientDep, body: NoteCreateRequest) -> NoteResponse:
    """Upload a note with JSON body (recorded_at + content)."""
    return await client.upload(
        patient_id=patient_id,
        recorded_at=body.recorded_at,
        content=body.content,
        store_in_object_storage=False,
    )


@router.post("/upload", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def upload_note_file(
    patient_id: UUID,
    client: NoteClientDep,
    recorded_at: Annotated[datetime, Form(description="When the note was recorded")],
    file: Annotated[UploadFile, File(description="Note content (e.g. .txt)")],
) -> NoteResponse:
    """Upload a note from a file; content is stored in object storage."""
    content = (await file.read()).decode("utf-8", errors="replace")
    return await client.upload(
        patient_id=patient_id,
        recorded_at=recorded_at,
        content=content,
        store_in_object_storage=True,
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


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(patient_id: UUID, note_id: UUID, client: NoteClientDep) -> NoteResponse:
    """Get a note by id. Returns 404 if note not found or not belonging to patient."""
    response = await client.get_by_id(note_id)
    if str(response.patient_id) != str(patient_id):
        from app.shared.exceptions import NotFoundException

        raise NotFoundException("Note not found")
    return response


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(patient_id: UUID, note_id: UUID, client: NoteClientDep) -> None:
    """Delete a note. Returns 404 if note not found or not belonging to patient."""
    response = await client.get_by_id(note_id)
    if str(response.patient_id) != str(patient_id):
        from app.shared.exceptions import NotFoundException

        raise NotFoundException("Note not found")
    await client.delete(note_id)
