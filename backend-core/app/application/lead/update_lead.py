"""Caso de uso: actualizar status, score y/o notas de un lead."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.application.dtos import LeadOutput, UpdateLeadInput, lead_to_output
from app.domain.lead.entity import LeadStatus
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import InvalidLeadError, LeadNotFoundError


class UpdateLeadUseCase:
    """Orquesta la actualización parcial de un lead."""

    def __init__(self, repo: LeadRepository) -> None:
        self._repo = repo

    async def execute(self, input: UpdateLeadInput) -> LeadOutput:
        # Validar UUID
        try:
            UUID(input.lead_id)
        except ValueError:
            raise LeadNotFoundError(f"Invalid lead ID: {input.lead_id}")

        lead = await self._repo.find_by_id(input.lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Lead not found: {input.lead_id}")

        if input.status is not None:
            if input.status not in LeadStatus.valid_statuses():
                raise InvalidLeadError(f"Invalid status: {input.status}")
            lead.status = LeadStatus(input.status)
            if input.status == LeadStatus.CONTACTED.value:
                lead.last_contacted_at = datetime.now(timezone.utc)
            elif input.status == LeadStatus.NOT_INTERESTED.value:
                lead.score = 0
        if input.score is not None:
            if not (0 <= input.score <= 100):
                raise InvalidLeadError(f"Score must be between 0 and 100")
            lead.score = input.score
        if input.notes is not None:
            lead.notes = input.notes
        if input.name is not None:
            lead.name = input.name

        lead.updated_at = datetime.now(timezone.utc)
        await self._repo.save(lead)
        return lead_to_output(lead)
