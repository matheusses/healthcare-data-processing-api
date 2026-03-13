"""NoteRepository implements INoteRepository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notes.domain import Note
from app.notes.interfaces.repositories.notes import INoteRepository
from app.shared.db.models.notes import NoteModel


class NoteRepository(INoteRepository):
    """Async note persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Note | None:
        result = await self._session.execute(select(NoteModel).where(NoteModel.id == id))
        row = result.scalar_one_or_none()
        return Note.model_validate(row) if row else None

    async def create(
        self,
        patient_id: UUID,
        recorded_at: datetime,
        content: str,
        storage_key: str | None = None,
    ) -> Note:
        model = NoteModel(
            patient_id=patient_id,
            recorded_at=recorded_at,
            content=content,
            storage_key=storage_key,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return Note.model_validate(model)

    async def delete(self, id: UUID) -> bool:
        result = await self._session.execute(select(NoteModel).where(NoteModel.id == id))
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list_by_patient(self, patient_id: UUID, limit: int = 100, offset: int = 0) -> list[Note]:
        stmt = (
            select(NoteModel)
            .where(NoteModel.patient_id == patient_id)
            .order_by(NoteModel.recorded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [Note.model_validate(row) for row in rows]

    async def count_by_patient(self, patient_id: UUID) -> int:
        stmt = select(func.count()).select_from(NoteModel).where(NoteModel.patient_id == patient_id)
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def update_storage_key(self, id: UUID, storage_key: str) -> Note | None:
        result = await self._session.execute(select(NoteModel).where(NoteModel.id == id))
        model = result.scalar_one_or_none()
        if not model:
            return None
        model.storage_key = storage_key
        await self._session.flush()
        await self._session.refresh(model)
        return Note.model_validate(model)
