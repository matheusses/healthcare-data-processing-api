"""Generic LLM client implementation (LangChain ChatOpenAI)."""

from app.config import settings
from app.shared.interfaces.llm.client import ILLMClient
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


class LLMClient(ILLMClient):
    """Wraps LangChain ChatOpenAI for invoke(system, user) -> str."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._model = ChatOpenAI(
            model=model or settings.OPENAI_SUMMARY_MODEL,
            openai_api_key=api_key or settings.OPENAI_API_KEY,
            temperature=0,
        )

    async def invoke(self, system: str, user: str) -> str:
        """Run LLM with system and user message; return assistant content as string."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
        result = await self._model.ainvoke(messages)
        return result.content if result and result.content else ""
