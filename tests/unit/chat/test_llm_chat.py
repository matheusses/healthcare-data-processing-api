"""PatientChatLlm tests with mocked ILLMClient."""

import pytest

from app.chat.llm import PatientChatLlm


class MockLLMClient:
    def __init__(self, response: str = "Answer text."):
        self._response = response

    async def invoke(self, system: str, user: str) -> str:
        return self._response


@pytest.mark.asyncio
async def test_chat_llm_invokes_with_context_and_message():
    llm = MockLLMClient("The patient has no allergies on record.")
    chat_llm = PatientChatLlm(llm)
    out = await chat_llm.answer("Patient: Jane. Notes: ...", "Any allergies?")
    assert "allergies" in out or "patient" in out.lower()
