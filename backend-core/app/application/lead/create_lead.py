"""Caso de uso: crear un lead (manual o automático desde webhook)."""

from __future__ import annotations

from uuid import UUID

from app.application.dtos import CreateLeadInput, LeadOutput, lead_to_output
from app.domain.lead.entity import Lead
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import InvalidLeadError


class CreateLeadUseCase:
    """Orquesta la creación de un lead.

    Si ya existe un lead con el mismo client_id + phone, retorna el existente
    (idempotencia para el webhook).
    """

    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    async def execute(self, input: CreateLeadInput) -> LeadOutput:
        if not input.client_id.strip():
            raise InvalidLeadError("client_id is required")
        if not input.phone.strip():
            raise InvalidLeadError("phone is required")

        # Verificar si ya existe (dedup por client_id + phone)
        existing = await self._repo.find_by_client_and_phone(
            client_id=input.client_id,
            phone=input.phone,
        )
        if existing is not None:
            return lead_to_output(existing)

        try:
            lead = Lead(
                client_id=UUID(input.client_id),
                phone=input.phone,
                name=input.name,
                source=input.source,
            )
        except ValueError as exc:
            raise InvalidLeadError(str(exc))

        await self._repo.save(lead)
        return lead_to_output(lead)
