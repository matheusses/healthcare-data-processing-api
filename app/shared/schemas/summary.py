"""Output format contract for future LLM-generated summaries (SOAP-aligned / discharge summary)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SOAPSummaryOutput(BaseModel):
    """
    Contract for LLM-generated SOAP-style summary.
    Used when implementing the actual summary endpoint (future work).
    """

    patient_id: UUID
    note_ids: list[UUID] = Field(..., description="Source note IDs")
    generated_at: datetime

    subjective: str = Field("", description="S: Chief complaints, history, patient statements")
    objective: str = Field("", description="O: Vitals, exam, labs")
    assessment: str = Field("", description="A: Assessment/diagnosis")
    plan: str = Field("", description="P: Plan, medications, follow-up")


class DischargeSummaryOutput(BaseModel):
    """
    Contract for LLM-generated discharge summary (future work).
    """

    patient_id: UUID
    note_ids: list[UUID] = Field(..., description="Source note IDs")
    generated_at: datetime

    admission_reason: str = Field("", description="Reason for admission")
    course_of_care: str = Field("", description="Summary of stay and interventions")
    discharge_diagnosis: list[str] = Field(default_factory=list)
    discharge_instructions: str = Field("", description="Patient instructions and follow-up")
    medications: list[str] = Field(default_factory=list)
