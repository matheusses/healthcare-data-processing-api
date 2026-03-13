"""Unit tests for Alembic migration setup.

Validates that metadata and migration files are consistent without requiring a DB.
"""

from pathlib import Path

from app.shared.db.database import Base
from app.shared.db.models.patients import PatientModel


def test_base_metadata_includes_all_tables() -> None:
    """All ORM models are registered on Base.metadata for autogenerate."""
    table_names = set(Base.metadata.tables.keys())
    assert "patients" in table_names
    assert "notes" in table_names
    assert "note_chunks" in table_names


def test_models_match_expected_tablenames() -> None:
    """ORM __tablename__ matches migration expectations."""
    from app.shared.db.models.notes import NoteModel
    from app.shared.db.models.note_chunks import NoteChunkModel

    assert PatientModel.__tablename__ == "patients"
    assert NoteModel.__tablename__ == "notes"
    assert NoteChunkModel.__tablename__ == "note_chunks"


def test_initial_migration_file_exists() -> None:
    """At least one migration file exists in versions."""
    versions_dir = Path(__file__).resolve().parents[3] / "alembic" / "versions"
    assert versions_dir.is_dir()
    py_files = [p for p in versions_dir.glob("*.py") if not p.name.startswith("__")]
    assert len(py_files) >= 1
