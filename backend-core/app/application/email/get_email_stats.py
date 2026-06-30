"""Caso de uso: obtener estadisticas de email marketing."""

from __future__ import annotations

from app.application.dtos import GetEmailStatsInput, EmailStatsOutput
from app.domain.email.repository import EmailRepository


class GetEmailStatsUseCase:
    """Retorna estadisticas de email marketing para un cliente."""

    def __init__(self, repo: EmailRepository) -> None:
        self._repo = repo

    async def execute(self, input: GetEmailStatsInput) -> EmailStatsOutput:
        stats = await self._repo.get_stats(client_id=input.client_id)
        return EmailStatsOutput(
            total_sent=stats["total_sent"],
            total_opened=stats["total_opened"],
            total_clicked=stats["total_clicked"],
            total_bounced=stats["total_bounced"],
            open_rate=stats["open_rate"],
            click_rate=stats["click_rate"],
            by_template=stats["by_template"],
        )
