"""Caso de uso: obtener estadísticas generales de conversaciones."""

from __future__ import annotations

from app.application.dtos import ConversationStatsOutput
from app.domain.conversation.repository import ConversationRepository


class GetConversationStatsUseCase:
    """Retorna estadísticas globales de conversaciones."""

    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    async def execute(self) -> ConversationStatsOutput:
        stats = await self._repo.get_stats()
        return ConversationStatsOutput(
            total_conversations=stats["total_conversations"],
            active_conversations=stats["active_conversations"],
            messages_today=stats["messages_today"],
            clients_with_conversations=stats["clients_with_conversations"],
        )
