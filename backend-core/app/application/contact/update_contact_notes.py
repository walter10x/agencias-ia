"""Caso de uso CRM-3: actualizar notas (y nombre) de un contacto.

Persiste vía Lead (upsert): si no hay lead, crea uno source=manual.
No añade tabla nueva (KISS / sin migración).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.application.contact.get_contact import ContactDetail, GetContactInput, GetContactUseCase
from app.domain.lead.entity import Lead
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import InvalidLeadError
from app.domain.shared.phone import normalize_phone


MAX_NOTES_LEN = 5000
MAX_NAME_LEN = 200


@dataclass(frozen=True, slots=True)
class UpdateContactNotesInput:
    client_id: str
    phone: str
    notes: str
    display_name: str | None = None


class UpdateContactNotesUseCase:
    def __init__(
        self,
        lead_repo: LeadRepository,
        get_contact: GetContactUseCase,
    ) -> None:
        self._leads = lead_repo
        self._get_contact = get_contact

    async def execute(self, input: UpdateContactNotesInput) -> ContactDetail:
        phone = normalize_phone(input.phone)
        if not phone:
            raise InvalidLeadError("phone is required")

        notes = (input.notes or "").strip()
        if len(notes) > MAX_NOTES_LEN:
            raise InvalidLeadError(f"notes must be at most {MAX_NOTES_LEN} characters")

        name: str | None = None
        if input.display_name is not None:
            name = input.display_name.strip()
            if len(name) > MAX_NAME_LEN:
                raise InvalidLeadError(f"display_name must be at most {MAX_NAME_LEN} characters")

        lead = await self._leads.find_by_client_and_phone(input.client_id, phone)
        if lead is None:
            lead = await self._leads.find_by_client_and_phone(
                input.client_id, phone.lstrip("+")
            )

        now = datetime.now(timezone.utc)
        if lead is None:
            try:
                lead = Lead(
                    client_id=UUID(input.client_id),
                    phone=phone,
                    name=name or "",
                    source="manual",
                    notes=notes,
                )
            except ValueError as exc:
                raise InvalidLeadError(str(exc)) from exc
        else:
            lead.notes = notes
            if name is not None:
                lead.name = name
            lead.updated_at = now

        await self._leads.save(lead)
        return await self._get_contact.execute(
            GetContactInput(client_id=input.client_id, phone=phone)
        )
