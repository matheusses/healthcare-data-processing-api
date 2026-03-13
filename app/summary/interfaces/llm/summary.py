"""Interface for SOAP summary LLM (module-specific)."""

from abc import ABC, abstractmethod


class ISummaryLlm(ABC):
    """Generate SOAP sections from patient context. Module-specific."""

    @abstractmethod
    async def generate_soap(self, patient_context: str) -> tuple[str, str, str, str]:
        """Return (subjective, objective, assessment, plan) from patient context."""
        ...
