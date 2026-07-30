"""Caso de uso CRM-5: marcar contacto como contactado (reactivación operativa)."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.contact.ensure_contact_lead import (
    EnsureContactLeadInput,
    EnsureContactLeadUseCase,
)
from app.application.contact.get_contact import ContactDetail, GetContactInput, GetContactUseCase
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import InvalidLeadError
from app.domain.shared.phone import normalize_phone


@dataclass(frozen=True, slots=True)
class MarkContactContactedInput:
    client_id: str
    phone: str


class MarkContactContactedUseCase:
    """Asegura lead y marca status=contacted + last_contacted_at."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        get_contact: GetContactUseCase,
    ) -> None:
        self._leads = lead_repo
        self._get_contact = get_contact

    async def execute(self, input: MarkContactContactedInput) -> ContactDetail:
        phone = normalize_phone(input.phone)
        if not phone:
            raise InvalidLeadError("phone is required")

        ensured = await EnsureContactLeadUseCase(self._leads).execute(
            EnsureContactLeadInput(
                client_id=input.client_id,
                phone=phone,
                source="manual",
            )
        )
        lead = await self._leads.find_by_id(ensured.lead_id)
        if lead is None:
            raise InvalidLeadError("Lead could not be ensured")

        lead.mark_contacted()
        await self._leads.save(lead)
        return await self._get_contact.execute(
            GetContactInput(client_id=input.client_id, phone=phone)
        )
