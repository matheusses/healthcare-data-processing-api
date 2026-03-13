"""SummaryService: ensure patient exists, gather context, call ISummaryLlm, return PatientSummaryResponse."""

from datetime import date, datetime, timezone
from uuid import UUID

from app.notes.interfaces.client.notes import INoteClient
from app.patients.interfaces.client.patients import IPatientClient
from app.shared.schemas.notes import NoteContentItem
from app.shared.exceptions import NotFoundException
from app.shared.schemas.summary import PatientHeading, PatientSummaryResponse
from app.summary.interfaces.llm.summary import ISummaryLlm


def _age_from_birth_date(birth_date: date) -> int:
    """Compute age in years from birth date."""
    today = date.today()
    return (today - birth_date).days // 365


def _build_patient_context_from_heading(
    heading: PatientHeading,
    note_items: list[NoteContentItem],
) -> str:
    """Build context string from heading and notes."""
    lines = [
        f"Patient: {heading.name}",
        f"Age: {heading.age}",
        f"Document number: {heading.document_number}",
        "",
        "--- Notes ---",
    ]
    for item in note_items:
        lines.append(f"[Note {item.note_id}]")
        lines.append(item.content or "(empty)")
        lines.append("")
    return "\n".join(lines).strip()


class SummaryService:
    """Orchestrates patient validation, note content, and SOAP generation."""

    def __init__(
        self,
        patient_client: IPatientClient,
        note_client: INoteClient,
        summary_llm: ISummaryLlm,
    ) -> None:
        self._patient_client = patient_client
        self._note_client = note_client
        self._summary_llm = summary_llm

    async def get_summary(self, patient_id: UUID) -> PatientSummaryResponse:
        """Ensure patient exists, get note contents, generate SOAP, return response."""
        patient = await self._patient_client.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient not found")
        note_items = await self._note_client.get_note_contents_for_patient(patient_id)
        heading = PatientHeading(
            name=patient.name,
            age=_age_from_birth_date(patient.birth_date),
            document_number=patient.document_number,
        )
        context = _build_patient_context_from_heading(heading, note_items)
        subjective, objective, assessment, plan = await self._summary_llm.generate_soap(context)
        return PatientSummaryResponse(
            patient_heading=heading,
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            generated_at=datetime.now(timezone.utc),
            note_ids=[n.note_id for n in note_items],
        )
