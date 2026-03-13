"""Shared pytest fixtures (unit)."""

# Disable OTLP export during tests so no connection to localhost:4317 and no
# "I/O operation on closed file" errors when the exporter's background thread
# logs during process shutdown.
import os

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio for pytest-asyncio."""
    return "asyncio"
