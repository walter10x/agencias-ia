"""Caso de uso: obtener estadísticas del pipeline de leads."""

from __future__ import annotations

from app.application.dtos import GetLeadStatsInput, LeadStatsOutput
from app.domain.lead.repository import LeadRepository


class GetLeadStatsUseCase:
    """Retorna estadísticas de leads para un cliente."""

    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    async def execute(self, input: GetLeadStatsInput) -> LeadStatsOutput:
        stats = await self._repo.get_stats(client_id=input.client_id)
        return LeadStatsOutput(
            total=stats["total"],
            by_status=stats["by_status"],
            conversion_rate=stats["conversion_rate"],
            new_today=stats["new_today"],
            avg_score=stats["avg_score"],
        )
