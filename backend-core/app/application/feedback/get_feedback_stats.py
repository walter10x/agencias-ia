"""Caso de uso: obtener estadísticas de feedback."""

from __future__ import annotations

from app.application.dtos import FeedbackStatsOutput, GetFeedbackStatsInput
from app.domain.feedback.repository import FeedbackRepository


class GetFeedbackStatsUseCase:
    """Retorna estadísticas de feedback para un cliente."""

    def __init__(self, repo: FeedbackRepository) -> None:
        self._repo = repo

    async def execute(self, input: GetFeedbackStatsInput) -> FeedbackStatsOutput:
        stats = await self._repo.get_stats(client_id=input.client_id)
        return FeedbackStatsOutput(
            total=stats["total"],
            average_rating=stats["average_rating"],
            rating_distribution=stats["rating_distribution"],
        )
