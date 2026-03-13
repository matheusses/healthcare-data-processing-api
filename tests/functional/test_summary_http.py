"""Functional HTTP tests for GET /patients/{id}/summary."""

def test_summary_route_registered(client):
    """Summary route is present under /patients."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert "/patients/{patient_id}/summary" in paths
    assert "get" in paths["/patients/{patient_id}/summary"]
