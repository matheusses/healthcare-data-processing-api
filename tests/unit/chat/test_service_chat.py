"""ChatService tests with mocked deps and IPatientChatLlm."""

from datetime import date
from uuid import uuid4

import pytest

from app.shared.exceptions import NotFoundException
from app.shared.schemas.chat import ChatResponse
from app.shared.schemas.notes import NoteContentItem
from app.shared.schemas.patients import PatientResponse
from app.chat.service import ChatService


class MockPatientClient:
    def __init__(self, patient: PatientResponse | None = None):
        self._patient = patient

    async def get_by_id(self, id):
        return self._patient


class MockNoteClient:
    def __init__(self, note_items: list[NoteContentItem] | None = None):
        self._note_items = note_items or []

    async def get_note_contents_for_patient(self, patient_id, query: str):
        return self._note_items


class MockChatLlm:
    def __init__(self, answer: str = "No medications listed."):
        self._answer = answer

    async def answer(self, patient_context: str, user_message: str) -> str:
        return self._answer


@pytest.mark.asyncio
async def test_chat_service_returns_response():
    patient_id = uuid4()
    patient = PatientResponse(
        id=patient_id,
        name="Test",
        birth_date=date(1990, 1, 1),
        document_number="doc-1",
    )
    svc = ChatService(
        patient_client=MockPatientClient(patient),
        note_client=MockNoteClient([NoteContentItem(note_id=uuid4(), content="Note")]),
        chat_llm=MockChatLlm("The patient is on aspirin."),
    )
    result = await svc.send(patient_id, "What medications?")
    assert isinstance(result, ChatResponse)
    assert "aspirin" in result.response


@pytest.mark.asyncio
async def test_chat_service_patient_not_found_raises():
    svc = ChatService(
        patient_client=MockPatientClient(None),
        note_client=MockNoteClient([]),
        chat_llm=MockChatLlm(),
    )
    with pytest.raises(NotFoundException) as exc_info:
        await svc.send(uuid4(), "Hello")
    assert "Patient not found" in str(exc_info.value)
