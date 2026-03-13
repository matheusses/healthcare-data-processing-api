"""DTO validation tests for note schemas."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.shared.schemas.notes import NoteCreateRequest, NoteListResponse, NoteResponse


def test_note_create_request_valid():
    data = NoteCreateRequest(
        recorded_at=datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
        content="S: Pt presents for check-up. O: BP 120/80. A: Healthy. P: Follow-up in 6 mo.",
    )
    assert data.content.startswith("S:")
    assert data.recorded_at.year == 2023


def test_note_create_request_empty_content_rejected():
    with pytest.raises(ValidationError):
        NoteCreateRequest(
            recorded_at=datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
            content="",
        )


def test_note_create_request_content_max_length():
    NoteCreateRequest(
        recorded_at=datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
        content="x" * 100,
    )
    with pytest.raises(ValidationError):
        NoteCreateRequest(
            recorded_at=datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
            content="x" * 100_001,
        )


def test_note_response_from_attributes():
    uid = uuid.uuid4()
    rec = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    r = NoteResponse(
        id=uid,
        recorded_at=rec,
    )
    assert r.id == uid
    assert r.recorded_at == rec


def test_note_list_response():
    items = []
    lst = NoteListResponse(items=items, total=0)
    assert lst.total == 0
    assert lst.items == []
