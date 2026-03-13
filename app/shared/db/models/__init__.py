"""ORM models; import here so Alembic autogenerate discovers all tables."""

from app.shared.db.models.note_chunks import NoteChunkModel
from app.shared.db.models.notes import NoteModel
from app.shared.db.models.patients import PatientModel

__all__ = ["NoteChunkModel", "NoteModel", "PatientModel"]
