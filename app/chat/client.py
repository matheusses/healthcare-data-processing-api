"""Public facade for chat; used by router."""

from uuid import UUID

from app.shared.schemas.chat import ChatResponse
from app.chat.interfaces.client.chat import IChatClient
from app.chat.service import ChatService


class ChatClient(IChatClient):
    """Facade for chat operations; delegates to ChatService."""

    def __init__(self, chat_service: ChatService) -> None:
        self._service = chat_service

    async def send(self, patient_id: UUID, message: str) -> ChatResponse:
        return await self._service.send(patient_id, message)
