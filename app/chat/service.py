"""ChatService: ensure patient exists, gather context, call IPatientChatLlm, return ChatResponse."""

from datetime import date
from uuid import UUID

from app.notes.interfaces.client.notes import INoteClient
from app.patients.interfaces.client.patients import IPatientClient
from app.shared.exceptions import NotFoundException
from app.shared.schemas.notes import NoteContentItem
from app.chat.interfaces.llm.chat import IPatientChatLlm
from app.shared.schemas.chat import ChatResponse
from app.shared.schemas.summary import PatientHeading


def _age_from_birth_date(birth_date: date) -> int:
    return (date.today() - birth_date).days // 365


def _build_context(heading: PatientHeading, note_items: list[NoteContentItem]) -> str:
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


class ChatService:
    """Orchestrates patient validation, note content, and chat LLM."""

    def __init__(
        self,
        patient_client: IPatientClient,
        note_client: INoteClient,
        chat_llm: IPatientChatLlm,
    ) -> None:
        self._patient_client = patient_client
        self._note_client = note_client
        self._chat_llm = chat_llm

    async def send(self, patient_id: UUID, message: str) -> ChatResponse:
        """Ensure patient exists, get note contents, call chat LLM, return response."""
        patient = await self._patient_client.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient not found")
        note_items = await self._note_client.get_note_contents_for_patient(patient_id, message)
        heading = PatientHeading(
            name=patient.name,
            age=_age_from_birth_date(patient.birth_date),
            document_number=patient.document_number,
        )
        context = _build_context(heading, note_items)
        response_text = await self._chat_llm.answer(context, message)
        return ChatResponse(response=response_text)
