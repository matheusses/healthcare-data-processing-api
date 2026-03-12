"""ORM models (internal; never exposed as API responses)."""

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.database import Base


class PatientModel(Base):
    """Patient table."""

    __tablename__ = "patients"

    document_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    id: Mapped[object] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
