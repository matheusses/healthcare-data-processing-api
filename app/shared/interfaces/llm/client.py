"""Abstract interface for generic LLM invocation (shared by summary and chat modules)."""

from abc import ABC, abstractmethod


class ILLMClient(ABC):
    """Generic LLM: call with system + user messages, get text back."""

    @abstractmethod
    async def invoke(self, system: str, user: str) -> str:
        """Run LLM with system and user message; return assistant text."""
        ...
