"""Public facade for patients; deps injected via parameter. Used by router and other modules."""

from typing import Literal
from uuid import UUID

from app.patients.interfaces.client.patients import IPatientClient
from app.shared.schemas.patients import PatientCreateRequest, PatientResponse, PatientUpdateRequest


class PatientClient(IPatientClient):
    """Facade for patient operations; receives service via parameter."""

    def __init__(self, patient_service: object) -> None:
        from app.patients.service import PatientService

        if not isinstance(patient_service, PatientService):
            raise TypeError("patient_service must be PatientService")
        self._service = patient_service

    async def get_by_id(self, id: UUID) -> PatientResponse | None:
        return await self._service.get_by_id(id)

    async def create(self, data: PatientCreateRequest) -> PatientResponse:
        return await self._service.create(data)

    async def update(self, id: UUID, data: PatientUpdateRequest) -> PatientResponse | None:
        return await self._service.update(id, data)

    async def delete(self, id: UUID) -> bool:
        return await self._service.delete(id)

    async def list_patients(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        order_by: Literal["name", "birth_date", "document_number"] = "name",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[PatientResponse]:
        return await self._service.list_patients(
            limit=limit, offset=offset, search=search, order_by=order_by, order_direction=order_direction
        )
