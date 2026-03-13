"""Interface for summary client."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.shared.schemas.summary import PatientSummaryResponse


class ISummaryClient(ABC):
    """Interface for patient summary operations."""

    @abstractmethod
    async def get_summary(self, patient_id: UUID) -> PatientSummaryResponse:
        """Return SOAP summary for the patient. Raises NotFoundException if patient not found."""
        ...
