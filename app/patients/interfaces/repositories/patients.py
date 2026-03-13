from abc import abstractmethod
from typing import Literal
from uuid import UUID
from app.patients.domain import Patient
from app.shared.schemas.patients import PatientCreateRequest, PatientUpdateRequest


class IPatientRepository:
    """Abstract interface for patient persistence."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Patient | None:
        """Return patient by id or None."""
        ...

    @abstractmethod
    async def get_by_document_number(self, document_number: str) -> Patient | None:
        """Return patient by document number or None."""
        ...

    @abstractmethod
    async def create(self, data: PatientCreateRequest) -> Patient:
        """Create patient and return internal DTO."""
        ...

    @abstractmethod
    async def update(self, id: UUID, data: PatientUpdateRequest) -> Patient | None:
        """Update patient; return internal DTO or None if not found."""
        ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete patient; return True if deleted."""
        ...

    @abstractmethod
    async def list_patients(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        order_by: Literal["name", "birth_date", "document_number"] = "name",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Patient]:
        """List patients with pagination. When search is set, filter by name similarity and order by relevance (most similar first)."""
        ...
