"""PatientChatLlm: Q&A prompt using shared ILLMClient."""

from app.shared.interfaces.llm.client import ILLMClient
from app.chat.interfaces.llm.chat import IPatientChatLlm

_SYSTEM_PROMPT = """You are a clinical assistant. You answer questions about a patient based only on the provided patient context (notes and metadata). Do not make up information. If the context does not contain enough information to answer, say so. Keep answers concise and clinically relevant. Do not include PHI beyond what is in the question or context."""


class PatientChatLlm(IPatientChatLlm):
    """Answers questions over patient context using ILLMClient."""

    def __init__(self, llm_client: ILLMClient) -> None:
        self._llm = llm_client

    async def answer(self, patient_context: str, user_message: str) -> str:
        """Build user message with context, invoke LLM, return response."""
        user = "Patient context:\n\n" + (patient_context or "(No notes or metadata available.)")
        user += "\n\nUser question: " + (user_message or "")
        return await self._llm.invoke(_SYSTEM_PROMPT, user)
