"""SummaryLlm tests with mocked ILLMClient (SOAP prompt building and parsing)."""

import pytest

from app.summary.llm import SummaryLlm, _parse_soap_response


class MockLLMClient:
    def __init__(self, response: str):
        self._response = response

    async def invoke(self, system: str, user: str) -> str:
        return self._response


def test_parse_soap_response_four_sections():
    text = """S: Patient reports headache.
O: BP 120/80.
A: Benign.
P: Follow up PRN."""
    s, o, a, p = _parse_soap_response(text)
    assert "headache" in s
    assert "120/80" in o
    assert "Benign" in a
    assert "PRN" in p


def test_parse_soap_response_multiline():
    text = """S: Line one.
Line two.
O: Objective here.
A: Assessment.
P: Plan."""
    s, o, a, p = _parse_soap_response(text)
    assert "Line two" in s
    assert "Objective here" in o


def test_parse_soap_response_empty_returns_empty_strings():
    s, o, a, p = _parse_soap_response("")
    assert s == ""
    assert o == ""
    assert a == ""
    assert p == ""


@pytest.mark.asyncio
async def test_summary_llm_calls_invoke_and_parses():
    llm = MockLLMClient("S: Subj text.\nO: Obj.\nA: Assess.\nP: Plan.")
    summary_llm = SummaryLlm(llm)
    s, o, a, p = await summary_llm.generate_soap("Patient: John. Notes: ...")
    assert "Subj" in s
    assert "Obj" in o
    assert "Assess" in a
    assert "Plan" in p
