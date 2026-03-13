"""SummaryService tests with mocked deps and ISummaryLlm."""

from uuid import uuid4

import pytest

from app.shared.exceptions import NotFoundException
from app.shared.schemas.notes import NoteContentItem
from app.shared.schemas.patients import PatientResponse
from app.shared.schemas.summary import PatientSummaryResponse
from app.summary.service import SummaryService


class MockPatientClient:
    def __init__(self, patient: PatientResponse | None = None):
        self._patient = patient

    async def get_by_id(self, id):
        return self._patient


class MockNoteClient:
    def __init__(self, note_items: list[NoteContentItem] | None = None):
        self._note_items = note_items or []

    async def get_note_contents_for_patient(self, patient_id):
        return self._note_items


class MockSummaryLlm:
    def __init__(self, s: str = "S", o: str = "O", a: str = "A", p: str = "P"):
        self._s, self._o, self._a, self._p = s, o, a, p

    async def generate_soap(self, patient_context: str):
        return (self._s, self._o, self._a, self._p)


@pytest.mark.asyncio
async def test_summary_service_returns_soap():
    from datetime import date

    patient_id = uuid4()
    patient = PatientResponse(
        id=patient_id,
        name="Test Patient",
        birth_date=date(1990, 5, 20),
        document_number="doc-1",
    )
    note_items = [NoteContentItem(note_id=uuid4(), content="Note text")]
    svc = SummaryService(
        patient_client=MockPatientClient(patient),
        note_client=MockNoteClient(note_items),
        summary_llm=MockSummaryLlm("Subj", "Obj", "Assess", "Plan"),
    )
    result = await svc.get_summary(patient_id)
    assert isinstance(result, PatientSummaryResponse)
    assert result.patient_heading.name == "Test Patient"
    assert result.subjective == "Subj"
    assert result.objective == "Obj"
    assert result.assessment == "Assess"
    assert result.plan == "Plan"
    assert result.generated_at is not None
    assert len(result.note_ids) == 1


@pytest.mark.asyncio
async def test_summary_service_patient_not_found_raises():
    patient_id = uuid4()
    svc = SummaryService(
        patient_client=MockPatientClient(None),
        note_client=MockNoteClient([]),
        summary_llm=MockSummaryLlm(),
    )
    with pytest.raises(NotFoundException) as exc_info:
        await svc.get_summary(patient_id)
    assert "Patient not found" in str(exc_info.value)
