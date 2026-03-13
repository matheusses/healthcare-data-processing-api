"""Functional HTTP tests for /patients/{patient_id}/notes (upload, list, delete)."""

from uuid import uuid4


def test_upload_file_missing_returns_422(client):
    """POST /upload without file returns 422."""
    r = client.post(
        f"/patients/{uuid4()}/notes/upload",
        data={},
    )
    assert r.status_code == 422


def test_notes_router_mounted(client):
    """Notes routes are registered under patients."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert any("/notes" in p and "patient" in p.lower() for p in paths)


def test_upload_note_requires_valid_body(client):
    """POST /upload with no file returns 422 (validation error)."""
    patient_id = uuid4()
    r = client.post(
        f"/patients/{patient_id}/notes/upload",
        data={},
    )
    assert r.status_code in (400, 422)
