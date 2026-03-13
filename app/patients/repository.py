"""PatientRepository implements IPatientRepository."""

from typing import Literal
from uuid import UUID

from sqlalchemy import bindparam, cast, func, or_, select
from sqlalchemy.types import String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.patients.interfaces.repositories.patients import IPatientRepository
from app.shared.db.models.patients import PatientModel
from app.shared.schemas.patients import PatientCreateRequest, PatientUpdateRequest
from app.patients.domain import Patient
from app.config import settings


class PatientRepository(IPatientRepository):
    """Async patient persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Patient | None:
        result = await self._session.execute(select(PatientModel).where(PatientModel.id == id))
        row = result.scalar_one_or_none()
        return Patient.model_validate(row) if row else None

    async def create(self, data: PatientCreateRequest) -> Patient:
        model = PatientModel(document_number=data.document_number, name=data.name, birth_date=data.birth_date)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return Patient.model_validate(model)

    async def update(self, id: UUID, data: PatientUpdateRequest) -> Patient | None:
        result = await self._session.execute(select(PatientModel).where(PatientModel.id == id))
        model = result.scalar_one_or_none()
        if not model:
            return None
        if data.name is not None:
            model.name = data.name
        if data.birth_date is not None:
            model.birth_date = data.birth_date
        await self._session.flush()
        await self._session.refresh(model)
        return Patient.model_validate(model)

    async def delete(self, id: UUID) -> bool:
        result = await self._session.execute(select(PatientModel).where(PatientModel.id == id))
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def get_by_document_number(self, document_number: str) -> Patient | None:
        result = await self._session.execute(select(PatientModel).where(PatientModel.document_number == document_number))
        row = result.scalar_one_or_none()
        return Patient.model_validate(row) if row else None

    async def list_patients(
        self,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        order_by: Literal["name", "birth_date", "document_number"] = "name",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Patient]:
        if search and search.strip():
            # Cast to text so similarity(text, text) is used (pg_trgm); avoids "function similarity(text, character varying) does not exist"
            search_param = cast(bindparam("search_term", type_=String()), Text())
            col_name = PatientModel.name
            col_document_number = PatientModel.document_number
            similarity_threshold = settings.PG_TRGM_SIMILARITY_THRESHOLD
            sim_name = func.similarity(col_name, search_param)
            sim_doc = func.similarity(col_document_number, search_param)
            stmt = (
                select(PatientModel)
                .where(
                    or_(
                        sim_name > similarity_threshold,
                        sim_doc > similarity_threshold,
                    )
                )
                .order_by(func.greatest(sim_name, sim_doc).desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self._session.execute(stmt, {"search_term": search.strip()})
        else:
            stmt = (
                select(PatientModel)
                .order_by(getattr(PatientModel, order_by).asc() if order_direction == "asc" else getattr(PatientModel, order_by).desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [Patient.model_validate(row) for row in rows]
