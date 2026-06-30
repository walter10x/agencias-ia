"""Caso de uso: obtener mensajes de una conversación."""

from __future__ import annotations

from uuid import UUID

from app.application.dtos import (
    GetConversationMessagesInput,
    MessageOutput,
    message_to_output,
)
from app.domain.conversation.repository import ConversationRepository
from app.domain.shared.errors import ConversationNotFoundError


class GetConversationMessagesUseCase:
    """Obtiene todos los mensajes de una conversación."""

    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    async def execute(self, input: GetConversationMessagesInput) -> tuple[list[MessageOutput], str, str]:
        # Validar UUID
        try:
            UUID(input.conversation_id)
        except ValueError:
            raise ConversationNotFoundError(f"Invalid conversation ID: {input.conversation_id}")

        # Verificar que la conversación existe
        conv = await self._repo.find_by_id(input.conversation_id)
        if conv is None:
            raise ConversationNotFoundError(
                f"Conversation not found: {input.conversation_id}"
            )

        messages = await self._repo.get_messages(input.conversation_id)
        return (
            [message_to_output(m) for m in messages],
            conv.wa_phone_number,
            conv.status,
        )
