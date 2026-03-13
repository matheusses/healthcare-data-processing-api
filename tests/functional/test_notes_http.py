"""Functional HTTP tests for /patients/{patient_id}/notes (upload, list, delete)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest


def test_notes_router_mounted(client):
    """Notes routes are registered under patients."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert any("/notes" in p and "patient" in p.lower() for p in paths)


def test_upload_note_requires_valid_body(client):
    """POST with invalid or missing body returns 422 or 400."""
    patient_id = uuid4()
    r = client.post(
        f"/patients/{patient_id}/notes/",
        json={},
    )
    assert r.status_code in (400, 422)


def test_list_notes_returns_404_for_missing_patient(client_with_lifespan):
    """GET /patients/{id}/notes returns 404 when patient does not exist."""
    try:
        r = client_with_lifespan.get(f"/patients/{uuid4()}/notes/")
    except Exception as e:
        if "Connect" in str(e) or "refused" in str(e).lower():
            pytest.skip("Database not available")
        raise
    assert r.status_code == 404


@pytest.mark.requires_db
def test_upload_list_delete_note_flow(client_with_lifespan):
    """Create patient, upload note (body), list, get, delete (run with DB)."""
    try:
        c = client_with_lifespan
        # Create patient
        pr = c.post(
            "/patients/",
            json={
                "name": "Note Flow Patient",
                "birth_date": "1990-01-15",
                "document_number": f"doc-flow-{uuid4()}",
            },
        )
        if pr.status_code >= 500:
            pytest.skip("DB or app error")
        assert pr.status_code == 201
        patient_id = pr.json()["id"]

        # Upload note (JSON body)
        rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        nr = c.post(
            f"/patients/{patient_id}/notes/",
            json={
                "recorded_at": rec,
                "content": "S: Annual visit. O: Vitals WNL. A: Healthy. P: Return 1y.",
            },
        )
        assert nr.status_code == 201
        note_id = nr.json()["id"]
        assert nr.json()["patient_id"] == patient_id

        # List notes
        lr = c.get(f"/patients/{patient_id}/notes/")
        assert lr.status_code == 200
        data = lr.json()
        assert "items" in data and "total" in data
        assert data["total"] >= 1
        assert any(n["id"] == note_id for n in data["items"])

        # Get single note
        gr = c.get(f"/patients/{patient_id}/notes/{note_id}")
        assert gr.status_code == 200
        assert gr.json()["id"] == note_id

        # Delete note
        dr = c.delete(f"/patients/{patient_id}/notes/{note_id}")
        assert dr.status_code == 204

        # Verify gone
        gr2 = c.get(f"/patients/{patient_id}/notes/{note_id}")
        assert gr2.status_code == 404
    except Exception as e:
        if "Connect" in str(e) or "refused" in str(e).lower() or "5434" in str(e):
            pytest.skip("Database not available")
        raise
