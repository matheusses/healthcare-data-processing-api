"""SummaryLlm: SOAP prompt and parsing using shared ILLMClient."""

import re
from pathlib import Path

from app.shared.interfaces.llm.client import ILLMClient
from app.summary.interfaces.llm.summary import ISummaryLlm

_SOAP_EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "docs" / "examples" / "soap_01.txt"

_SYSTEM_PROMPT = """You are a clinical assistant. Your task is to synthesize patient notes into a single, coherent SOAP note.

SOAP format:
- **Subjective (S):** The patient's reported symptoms, history, chief complaints, and statements.
- **Objective (O):** The clinician's observations, exam findings, vitals, and test results.
- **Assessment (A):** The clinician's diagnoses or summary of the case.
- **Plan (P):** The treatment plan, medications, follow-up, and next steps.

Output MUST use exactly these section labels at the start of each section:
S:
O:
A:
P:

Each section content should be concise and clinical. Do not include headers like "SOAP Note" or "Patient:" in the sections—only the four blocks S:/O:/A:/P: with their content.
"""


def _load_example() -> str:
    """Load few-shot example from docs/examples/soap_01.txt if present."""
    if _SOAP_EXAMPLE_PATH.is_file():
        return _SOAP_EXAMPLE_PATH.read_text(encoding="utf-8").strip()
    return ""


def _parse_soap_response(text: str) -> tuple[str, str, str, str]:
    """Extract S, O, A, P sections from LLM output. Sections start with 'S:', 'O:', 'A:', 'P:'."""
    text = (text or "").strip()
    pattern = re.compile(
        r"^(S|O|A|P)\s*:\s*",
        re.IGNORECASE | re.MULTILINE,
    )
    parts: dict[str, str] = {"S": "", "O": "", "A": "", "P": ""}
    current = None
    current_text: list[str] = []
    for line in text.split("\n"):
        match = pattern.match(line)
        if match:
            if current is not None:
                parts[current] = "\n".join(current_text).strip()
            current = match.group(1).upper()
            rest = line[match.end() :].strip()
            current_text = [rest] if rest else []
        elif current is not None:
            current_text.append(line)
    if current is not None:
        parts[current] = "\n".join(current_text).strip()
    return (parts["S"], parts["O"], parts["A"], parts["P"])


class SummaryLlm(ISummaryLlm):
    """Generates SOAP from patient context using ILLMClient."""

    def __init__(self, llm_client: ILLMClient) -> None:
        self._llm = llm_client
        self._example = _load_example()

    async def generate_soap(self, patient_context: str) -> tuple[str, str, str, str]:
        """Build SOAP prompt, invoke LLM, parse into (S, O, A, P)."""
        user = "Patient notes and metadata:\n\n" + (patient_context or "(No notes available.)")
        if self._example:
            user += "\n\nExample of desired SOAP format:\n\n" + self._example
        user += "\n\nProduce a single SOAP note (S:/O:/A:/P:) from the patient notes above."
        response = await self._llm.invoke(_SYSTEM_PROMPT, user)
        return _parse_soap_response(response)
