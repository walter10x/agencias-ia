"""Caso de uso: listar leads de un cliente con filtros."""

from __future__ import annotations

from app.application.dtos import LeadOutput, ListLeadsInput, lead_to_output
from app.domain.lead.repository import LeadRepository


class ListLeadsUseCase:
    """Orquesta la consulta paginada y filtrada de leads."""

    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    async def execute(
        self, input: ListLeadsInput
    ) -> tuple[list[LeadOutput], int]:
        if not input.client_id.strip():
            raise ValueError("client_id is required")

        leads = await self._repo.list_by_client(
            client_id=input.client_id,
            status=input.status,
            limit=input.limit,
            offset=input.offset,
        )
        total = await self._repo.count_by_client(
            client_id=input.client_id,
            status=input.status,
        )

        return [lead_to_output(l) for l in leads], total
