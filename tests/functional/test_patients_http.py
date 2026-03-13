"""Functional HTTP tests for /patients."""


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
