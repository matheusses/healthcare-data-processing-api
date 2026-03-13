"""Note domain entities and value objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Note(BaseModel):
    """Domain entity for a patient note."""

    id: UUID
    patient_id: UUID
    recorded_at: datetime
    content: str
    storage_key: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
