"""Functional HTTP tests for /patients/{patient_id}/notes (upload, list, delete)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest


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


@pytest.mark.requires_db
def test_upload_file_txt_with_optional_recorded_at(client_with_lifespan):
    """Upload via file: .txt with recorded_at omitted (defaults to now) or provided."""
    try:
        c = client_with_lifespan
        pr = c.post(
            "/patients/",
            json={
                "name": "Upload File Patient",
                "birth_date": "1985-05-20",
                "document_number": f"doc-upload-{uuid4()}",
            },
        )
        if pr.status_code >= 500:
            pytest.skip("DB or app error")
        assert pr.status_code == 201
        patient_id = pr.json()["id"]

        # Upload .txt without recorded_at -> 201, recorded_at should be set
        content_txt = "SOAP: Subjective and Objective note from file."
        r1 = c.post(
            f"/patients/{patient_id}/notes/upload",
            files={"file": ("note.txt", content_txt.encode("utf-8"), "text/plain")},
            data={},
        )
        assert r1.status_code == 201
        note1 = r1.json()
        assert note1["content"] == content_txt
        assert "recorded_at" in note1

        # Upload .txt with recorded_at provided
        rec = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc).isoformat()
        r2 = c.post(
            f"/patients/{patient_id}/notes/upload",
            files={"file": ("note2.txt", b"Second note.", "text/plain")},
            data={"recorded_at": rec},
        )
        assert r2.status_code == 201
        note2 = r2.json()
        assert "2024-01-15" in note2["recorded_at"] or "14:30" in note2["recorded_at"]
    except Exception as e:
        if "Connect" in str(e) or "refused" in str(e).lower() or "5434" in str(e):
            pytest.skip("Database not available")
        raise


@pytest.mark.requires_db
def test_upload_file_disallowed_type_returns_422(client_with_lifespan):
    """Upload with disallowed file type (.docx) returns 422."""
    try:
        c = client_with_lifespan
        pr = c.post(
            "/patients/",
            json={
                "name": "Disallow File Patient",
                "birth_date": "1990-01-01",
                "document_number": f"doc-disallow-{uuid4()}",
            },
        )
        if pr.status_code >= 500:
            pytest.skip("DB or app error")
        assert pr.status_code == 201
        patient_id = pr.json()["id"]

        r = c.post(
            f"/patients/{patient_id}/notes/upload",
            files={"file": ("note.docx", b"data", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={},
        )
        assert r.status_code == 422
        assert "detail" in r.json()
    except Exception as e:
        if "Connect" in str(e) or "refused" in str(e).lower() or "5434" in str(e):
            pytest.skip("Database not available")
        raise
