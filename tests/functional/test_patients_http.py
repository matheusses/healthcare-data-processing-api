"""Functional HTTP tests for /patients (require running app with DB)."""

import pytest


def test_openapi_available(client):
    """Docs and OpenAPI are exposed."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "openapi" in data
    assert "paths" in data


def test_patients_router_mounted(client):
    """Patients prefix is registered."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert any(p.startswith("/patients") for p in paths)


@pytest.mark.requires_db
def test_list_patients_empty_or_ok(client_with_lifespan):
    """GET /patients/ returns 200 and list of patient DTOs (run with: pytest -m requires_db when DB is up)."""
    try:
        r = client_with_lifespan.get("/patients/")
    except Exception as e:
        if "Connect" in str(e) or "refused" in str(e).lower() or "5434" in str(e):
            pytest.skip("Database not available (connection refused)")
        raise
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    for item in data:
        assert "id" in item and "name" in item
