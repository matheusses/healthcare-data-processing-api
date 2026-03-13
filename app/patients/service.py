"""PatientService: orchestration and transaction boundary."""

from typing import Literal
from uuid import UUID

from app.patients.domain import Patient
from app.shared.exceptions import DomainException, NotFoundException
from app.patients.interfaces.repositories.patients import IPatientRepository
from app.shared.schemas.patients import (
    PatientCreateRequest,
    PatientResponse,
    PatientUpdateRequest,
)


class PatientService:
    """Patient business logic; uses repository via interface."""

    def __init__(self, patient_repository: IPatientRepository) -> None:
        self._repo = patient_repository

    async def get_by_id(self, id: UUID) -> PatientResponse | None:
        patient = await self._repo.get_by_id(id)
        if not patient:
            raise NotFoundException("Patient not found")
        return self._to_response(patient)

    async def create(self, data: PatientCreateRequest) -> PatientResponse:
        existing = await self._repo.get_by_document_number(data.document_number)
        if existing:
            raise DomainException(
                f"Patient with document number '{data.document_number}' already exists",
                code="DUPLICATE_DOCUMENT_NUMBER",
            )
        internal = await self._repo.create(data)
        return self._to_response(internal)

    async def update(self, id: UUID, data: PatientUpdateRequest) -> PatientResponse | None:
        internal = await self._repo.update(id, data)
        if not internal:
            return None
        return self._to_response(internal)

    async def delete(self, id: UUID) -> bool:
        deleted = await self._repo.delete(id)
        if not deleted:
            raise NotFoundException("Patient not found")
        return deleted

    async def list_patients(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        order_by: Literal["name", "birth_date", "document_number"] = "name",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[PatientResponse]:
        internals = await self._repo.list_patients(
            limit=limit,
            offset=offset,
            search=search,
            order_by=order_by,
            order_direction=order_direction,
        )
        return [self._to_response(internal) for internal in internals]

    def _to_response(self, patient: Patient) -> PatientResponse:
        return PatientResponse(
            id=patient.id,
            name=patient.name,
            birth_date=patient.birth_date,
            document_number=patient.document_number,
        )
