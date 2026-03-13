from abc import ABC, abstractmethod
from typing import Literal
from uuid import UUID

from app.shared.schemas.patients import PatientCreateRequest, PatientResponse, PatientUpdateRequest


class IPatientClient(ABC):
    """Interface for patient client operations."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> PatientResponse | None: ...

    @abstractmethod
    async def create(self, data: PatientCreateRequest) -> PatientResponse: ...

    @abstractmethod
    async def update(self, id: UUID, data: PatientUpdateRequest) -> PatientResponse | None: ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool: ...

    @abstractmethod
    async def list_patients(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        order_by: Literal["name", "birth_date", "document_number"] = "name",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[PatientResponse]: ...
