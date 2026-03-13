"""DTO validation tests for chat schemas."""

import pytest
from pydantic import ValidationError

from app.shared.schemas.chat import ChatRequest, ChatResponse


def test_chat_request_valid():
    r = ChatRequest(message="What medications is the patient on?")
    assert r.message == "What medications is the patient on?"


def test_chat_request_empty_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_message_too_long_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 16_385)


def test_chat_response_valid():
    r = ChatResponse(response="The patient has no current medications listed.")
    assert "medications" in r.response
