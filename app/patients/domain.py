"""Patient domain entities and value objects."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class Patient(BaseModel):
    """Domain entity for a patient."""

    id: UUID
    name: str
    birth_date: date
    document_number: str

    model_config = {"from_attributes": True}
