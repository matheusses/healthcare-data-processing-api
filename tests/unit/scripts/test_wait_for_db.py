"""Unit tests for scripts.wait_for_db."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from scripts.wait_for_db import wait_for_db


@pytest.mark.asyncio
async def test_wait_for_db_succeeds_when_connect_works():
    with patch("scripts.wait_for_db.Settings") as mock_settings:
        mock_settings.return_value.database_url = "postgresql+asyncpg://u:p@localhost:5432/db"
        with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = AsyncMock(close=AsyncMock())
            result = await wait_for_db(timeout_seconds=5, interval=0.01)
    assert result is True
    mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_db_times_out_when_connect_fails():
    with patch("scripts.wait_for_db.Settings") as mock_settings:
        mock_settings.return_value.database_url = "postgresql+asyncpg://u:p@localhost:5432/db"
        with patch(
            "asyncpg.connect", new_callable=AsyncMock, side_effect=Exception("connection refused")
        ):
            result = await wait_for_db(timeout_seconds=0.2, interval=0.05)
    assert result is False


@pytest.mark.asyncio
async def test_wait_for_db_skips_wait_for_non_postgres_url():
    # Patch where the script resolves Settings so it gets a non-Postgres URL
    with patch("scripts.wait_for_db.Settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(database_url="sqlite+aiosqlite:///local.db")
        result = await wait_for_db(timeout_seconds=1, interval=0.01)
    assert result is True
