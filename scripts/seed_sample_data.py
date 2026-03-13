#!/usr/bin/env python3
"""Seed the database with sample patients and notes for demo or local development.

Run after migrations (e.g. after ./scripts/initial_db.sh). Does not overwrite existing
data by default: if any patients exist, exits without changes. Use --force to add
sample data even when the DB already has records (idempotent: skips if demo patients
already exist).

Usage:
  uv run python scripts/seed_sample_data.py
  uv run python scripts/seed_sample_data.py --force

Requires DATABASE_URL in environment or .env (see .env.example).
"""

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timezone

# Ensure project root is on path when run as script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.shared.db.models.notes import NoteModel
from app.shared.db.models.patients import PatientModel


# Demo document numbers used for idempotency
DEMO_DOCUMENT_NUMBERS = ("DEMO-001", "DEMO-002")


async def seed(session: AsyncSession, force: bool) -> int:
    """Insert sample patients and notes. Returns number of patients created."""
    if not force:
        existing = await session.execute(select(PatientModel))
        if existing.scalars().first() is not None:
            print(
                "Database already has patients; skipping seed (use --force to add demo data anyway)."
            )
            return 0

    # Idempotent: skip if demo patients already exist
    for doc in DEMO_DOCUMENT_NUMBERS:
        r = await session.execute(select(PatientModel).where(PatientModel.document_number == doc))
        if r.scalar_one_or_none() is not None:
            print(f"Demo patient {doc} already exists; skipping seed.")
            return 0

    p1 = PatientModel(
        document_number="DEMO-001",
        name="Jane Doe",
        birth_date=date(1985, 3, 15),
    )
    p2 = PatientModel(
        document_number="DEMO-002",
        name="John Smith",
        birth_date=date(1990, 7, 22),
    )
    session.add_all([p1, p2])
    await session.flush()

    # Sample notes (storage_key placeholder; no file in MinIO required for demo)
    now = datetime.now(timezone.utc)
    session.add_all(
        [
            NoteModel(
                patient_id=p1.id,
                recorded_at=now,
                storage_key="seed/demo-note-1.txt",
            ),
            NoteModel(
                patient_id=p1.id,
                recorded_at=now,
                storage_key="seed/demo-note-2.txt",
            ),
            NoteModel(
                patient_id=p2.id,
                recorded_at=now,
                storage_key="seed/demo-note-3.txt",
            ),
        ]
    )
    await session.commit()
    print("Sample data seeded: 2 patients, 3 notes (DEMO-001, DEMO-002).")
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database with sample patients and notes.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Add demo data even if DB already has patients (idempotent: skips if demo patients exist).",
    )
    args = parser.parse_args()

    settings = Settings()
    if not settings.DATABASE_URL or not settings.DATABASE_URL.strip():
        print(
            "DATABASE_URL is not set. Copy .env.example to .env and set DATABASE_URL (or run after ./scripts/initial_db.sh).",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def run() -> None:
        async with session_factory() as session:
            await seed(session, args.force)

    asyncio.run(run())


if __name__ == "__main__":
    main()
