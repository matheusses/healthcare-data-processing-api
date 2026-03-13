"""Public facade for summary; used by router."""

from uuid import UUID

from app.shared.schemas.summary import PatientSummaryResponse
from app.summary.interfaces.client.summary import ISummaryClient
from app.summary.service import SummaryService


class SummaryClient(ISummaryClient):
    """Facade for summary operations; delegates to SummaryService."""

    def __init__(self, summary_service: SummaryService) -> None:
        self._service = summary_service

    async def get_summary(self, patient_id: UUID) -> PatientSummaryResponse:
        return await self._service.get_summary(patient_id)
