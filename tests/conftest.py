"""Shared pytest fixtures (unit)."""

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio for pytest-asyncio."""
    return "asyncio"
