"""Interface for patient chat LLM (module-specific)."""

from abc import ABC, abstractmethod


class IPatientChatLlm(ABC):
    """Answer user questions given patient context. Module-specific."""

    @abstractmethod
    async def answer(self, patient_context: str, user_message: str) -> str:
        """Return answer string based on patient context and user message."""
        ...
