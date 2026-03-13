"""Unit tests for scripts.seed_sample_data."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.seed_sample_data import DEMO_DOCUMENT_NUMBERS, seed


def _make_session():
    """Session with execute as AsyncMock so await session.execute() works."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_seed_skips_when_patients_exist_and_not_force():
    """When force=False and any patient exists, seed returns 0 and does not insert."""
    session = _make_session()
    result_scalar = MagicMock()
    result_scalar.scalars.return_value.first.return_value = MagicMock()
    session.execute.return_value = result_scalar

    count = await seed(session, force=False)

    assert count == 0
    session.add_all.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_seed_skips_when_demo_patient_exists_with_force():
    """When force=True but a demo patient (DEMO-001) already exists, seed returns 0."""
    session = _make_session()
    existing_demo = MagicMock()
    session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=existing_demo)),
    ]

    count = await seed(session, force=True)

    assert count == 0
    session.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_seed_inserts_when_no_patients_and_not_force():
    """When force=False and no patients exist, seed inserts 2 patients and 3 notes."""
    session = _make_session()
    no_patients = MagicMock()
    no_patients.scalars.return_value.first.return_value = None
    no_demo = MagicMock()
    no_demo.scalar_one_or_none.return_value = None
    session.execute.side_effect = [no_patients, no_demo, no_demo]

    count = await seed(session, force=False)

    assert count == 2
    assert session.add_all.call_count >= 1
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_seed_inserts_when_force_and_no_demo_patients():
    """When force=True and no demo patients exist, seed inserts data."""
    session = _make_session()
    no_demo = MagicMock()
    no_demo.scalar_one_or_none.return_value = None
    session.execute.side_effect = [no_demo, no_demo]

    count = await seed(session, force=True)

    assert count == 2
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_demo_document_numbers_constant():
    """DEMO document numbers used for idempotency are defined."""
    assert "DEMO-001" in DEMO_DOCUMENT_NUMBERS
    assert "DEMO-002" in DEMO_DOCUMENT_NUMBERS
