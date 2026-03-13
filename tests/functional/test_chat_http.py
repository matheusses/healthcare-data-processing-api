"""Functional HTTP tests for POST /patients/{id}/chat."""

from uuid import uuid4


def test_chat_route_registered(client):
    """Chat route is present under /patients."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert "/patients/{patient_id}/chat" in paths
    assert "post" in paths["/patients/{patient_id}/chat"]


def test_chat_empty_message_returns_422(client):
    """POST with empty or missing message returns 422."""
    r = client.post(
        f"/patients/{uuid4()}/chat",
        json={"message": ""},
    )
    assert r.status_code == 422


def test_chat_missing_body_returns_422(client):
    """POST without body or message returns 422."""
    r = client.post(f"/patients/{uuid4()}/chat", json={})
    assert r.status_code == 422
