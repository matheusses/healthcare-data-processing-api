"""Note domain entities and value objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel



class Note(BaseModel):
    """Domain entity for a patient note."""

    id: UUID
    patient_id: UUID
    recorded_at: datetime
    storage_key: str


    model_config = {"from_attributes": True}
