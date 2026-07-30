"""Caso de uso CRM-4: asegurar Lead/contacto para un teléfono del tenant.

Idempotente: si ya existe lead (mismo client + phone normalizado),
opcionalmente rellena nombre vacío y actualiza last_contacted_at.
Si no existe, crea uno. No rompe el flujo si falla (el llamador decide).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.domain.lead.entity import Lead
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import InvalidLeadError
from app.domain.shared.phone import normalize_phone


@dataclass(frozen=True, slots=True)
class EnsureContactLeadInput:
    client_id: str
    phone: str
    name: str = ""
    source: str = "whatsapp"


@dataclass(frozen=True, slots=True)
class EnsureContactLeadOutput:
    lead_id: str
    created: bool
    phone: str


class EnsureContactLeadUseCase:
    def __init__(self, lead_repo: LeadRepository) -> None:
        self._leads = lead_repo

    async def execute(self, input: EnsureContactLeadInput) -> EnsureContactLeadOutput:
        phone = normalize_phone(input.phone)
        if not phone:
            raise InvalidLeadError("phone is required")
        if not input.client_id.strip():
            raise InvalidLeadError("client_id is required")

        source = (input.source or "whatsapp").strip().lower()
        if source not in Lead.VALID_SOURCES:
            raise InvalidLeadError(f"Invalid source: {source}")

        name = (input.name or "").strip()

        lead = await self._leads.find_by_client_and_phone(input.client_id, phone)
        if lead is None:
            lead = await self._leads.find_by_client_and_phone(
                input.client_id, phone.lstrip("+")
            )

        now = datetime.now(timezone.utc)
        if lead is not None:
            dirty = False
            if name and not (lead.name or "").strip():
                lead.name = name
                dirty = True
            if source == "whatsapp":
                lead.last_contacted_at = now
                dirty = True
            if dirty:
                lead.updated_at = now
                await self._leads.save(lead)
            return EnsureContactLeadOutput(
                lead_id=str(lead.id), created=False, phone=phone
            )

        try:
            lead = Lead(
                client_id=UUID(input.client_id),
                phone=phone,
                name=name,
                source=source,
            )
        except ValueError as exc:
            raise InvalidLeadError(str(exc)) from exc

        if source == "whatsapp":
            lead.last_contacted_at = now

        await self._leads.save(lead)
        return EnsureContactLeadOutput(
            lead_id=str(lead.id), created=True, phone=phone
        )
