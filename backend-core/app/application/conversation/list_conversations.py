"""Caso de uso: listar conversaciones de un cliente."""

from __future__ import annotations

from app.application.dtos import (
    ConversationOutput,
    ListConversationsInput,
    conversation_to_output,
)
from app.domain.conversation.repository import ConversationRepository


class ListConversationsUseCase:
    """Orquesta la consulta paginada de conversaciones."""

    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    async def execute(self, input: ListConversationsInput) -> tuple[list[ConversationOutput], int]:
        if not input.client_id.strip():
            raise ValueError("client_id is required")

        conversations = await self._repo.list_by_client(
            client_id=input.client_id,
            limit=input.limit,
            offset=input.offset,
        )
        total = await self._repo.count_by_client(client_id=input.client_id)

        return [conversation_to_output(c) for c in conversations], total
