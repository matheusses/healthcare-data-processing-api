"""Functional HTTP tests for GET /patients/{id}/summary."""

from uuid import uuid4


def test_summary_route_registered(client):
    """Summary route is present under /patients."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert "/patients/{patient_id}/summary" in paths
    assert "get" in paths["/patients/{patient_id}/summary"]


def test_summary_returns_404_for_missing_patient(client_with_lifespan):
    """GET /patients/{id}/summary returns 404 when patient does not exist."""
    try:
        r = client_with_lifespan.get(f"/patients/{uuid4()}/summary")
    except Exception as e:
        if "Connect" in str(e) or "refused" in str(e).lower():
            import pytest
            pytest.skip("Database not available")
        raise
    assert r.status_code == 404
    assert "detail" in r.json()
