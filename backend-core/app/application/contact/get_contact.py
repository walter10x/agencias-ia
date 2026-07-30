"""Casos de uso CRM-1: ficha de contacto (agregación solo lectura)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.appointment.repository import AppointmentRepository
from app.domain.conversation.repository import ConversationRepository
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import ContactNotFoundError
from app.domain.shared.phone import normalize_phone, phones_match


@dataclass(frozen=True, slots=True)
class ContactLeadSnippet:
    id: str
    status: str
    score: int
    notes: str
    name: str


@dataclass(frozen=True, slots=True)
class ContactConversationSnippet:
    id: str
    status: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ContactAppointmentSnippet:
    id: str
    starts_at: str
    status: str
    contact_name: str


@dataclass(frozen=True, slots=True)
class ContactDetail:
    client_id: str
    phone: str
    display_name: str
    lead: ContactLeadSnippet | None
    conversations: list[ContactConversationSnippet]
    appointments: list[ContactAppointmentSnippet]
    last_activity_at: str | None


@dataclass(frozen=True, slots=True)
class ContactSummary:
    phone: str
    display_name: str
    lead_status: str | None
    last_activity_at: str | None
    has_conversation: bool
    has_appointments: bool
    inactive_days: int | None = None


@dataclass(frozen=True, slots=True)
class GetContactInput:
    client_id: str
    phone: str


@dataclass(frozen=True, slots=True)
class ListContactsInput:
    client_id: str
    limit: int = 50
    offset: int = 0
    inactive_days_min: int | None = None


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _max_iso(*values: str | None) -> str | None:
    present = [v for v in values if v]
    return max(present) if present else None


def inactive_days_since(last_activity_at: str | None, now: datetime) -> int | None:
    """Días enteros desde last_activity hasta now. None si no hay actividad."""
    if not last_activity_at:
        return None
    try:
        last = datetime.fromisoformat(last_activity_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    now_aware = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    delta = now_aware - last
    return max(0, delta.days)


class GetContactUseCase:
    """Agrega lead + conversación + citas por (tenant, teléfono)."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        conversation_repo: ConversationRepository,
        appointment_repo: AppointmentRepository,
    ) -> None:
        self._leads = lead_repo
        self._conversations = conversation_repo
        self._appointments = appointment_repo

    async def execute(self, input: GetContactInput) -> ContactDetail:
        phone = normalize_phone(input.phone)
        if not phone:
            raise ContactNotFoundError("phone is required")

        lead = await self._leads.find_by_client_and_phone(input.client_id, phone)
        if lead is None:
            # Reintento sin '+' por datos legacy
            lead = await self._leads.find_by_client_and_phone(
                input.client_id, phone.lstrip("+")
            )

        conversation = await self._conversations.find_by_client_and_phone(
            input.client_id, phone
        )
        if conversation is None:
            conversation = await self._conversations.find_by_client_and_phone(
                input.client_id, phone.lstrip("+")
            )

        all_appts = await self._appointments.list_by_client(
            client_id=input.client_id, limit=200, offset=0
        )
        appts = [a for a in all_appts if phones_match(a.contact_phone, phone)]

        if lead is None and conversation is None and not appts:
            raise ContactNotFoundError(f"Contact not found: {phone}")

        lead_snip = None
        if lead is not None:
            lead_snip = ContactLeadSnippet(
                id=str(lead.id),
                status=lead.status.value if hasattr(lead.status, "value") else str(lead.status),
                score=lead.score,
                notes=lead.notes or "",
                name=lead.name or "",
            )

        conv_snips: list[ContactConversationSnippet] = []
        if conversation is not None:
            conv_snips.append(
                ContactConversationSnippet(
                    id=str(conversation.id),
                    status=conversation.status,
                    updated_at=_iso(conversation.updated_at) or "",
                )
            )

        appt_snips = [
            ContactAppointmentSnippet(
                id=str(a.id),
                starts_at=_iso(a.starts_at) or "",
                status=a.status.value if hasattr(a.status, "value") else str(a.status),
                contact_name=a.contact_name or "",
            )
            for a in sorted(appts, key=lambda x: x.starts_at, reverse=True)
        ]

        display = (
            (lead_snip.name if lead_snip and lead_snip.name else "")
            or next((s.contact_name for s in appt_snips if s.contact_name), "")
            or phone
        )

        last_activity = _max_iso(
            _iso(lead.updated_at) if lead else None,
            _iso(conversation.updated_at) if conversation else None,
            appt_snips[0].starts_at if appt_snips else None,
        )

        return ContactDetail(
            client_id=input.client_id,
            phone=phone,
            display_name=display,
            lead=lead_snip,
            conversations=conv_snips,
            appointments=appt_snips,
            last_activity_at=last_activity,
        )


class ListContactsUseCase:
    """Lista personas del tenant uniendo teléfonos de leads y conversaciones."""

    def __init__(
        self,
        lead_repo: LeadRepository,
        conversation_repo: ConversationRepository,
        appointment_repo: AppointmentRepository,
        now_provider=None,
    ) -> None:
        self._leads = lead_repo
        self._conversations = conversation_repo
        self._appointments = appointment_repo
        self._now = now_provider or (lambda: datetime.now(timezone.utc))

    async def execute(self, input: ListContactsInput) -> tuple[list[ContactSummary], int]:
        leads = await self._leads.list_by_client(
            input.client_id, limit=200, offset=0
        )
        conversations = await self._conversations.list_by_client(
            input.client_id, limit=200, offset=0
        )
        appointments = await self._appointments.list_by_client(
            input.client_id, limit=200, offset=0
        )

        by_phone: dict[str, ContactSummary] = {}

        for lead in leads:
            phone = normalize_phone(lead.phone)
            if not phone:
                continue
            status = lead.status.value if hasattr(lead.status, "value") else str(lead.status)
            by_phone[phone] = ContactSummary(
                phone=phone,
                display_name=lead.name or phone,
                lead_status=status,
                last_activity_at=_iso(lead.updated_at),
                has_conversation=False,
                has_appointments=False,
            )

        for conv in conversations:
            phone = normalize_phone(conv.wa_phone_number)
            if not phone:
                continue
            existing = by_phone.get(phone)
            last = _iso(conv.updated_at)
            if existing is None:
                by_phone[phone] = ContactSummary(
                    phone=phone,
                    display_name=phone,
                    lead_status=None,
                    last_activity_at=last,
                    has_conversation=True,
                    has_appointments=False,
                )
            else:
                by_phone[phone] = ContactSummary(
                    phone=existing.phone,
                    display_name=existing.display_name,
                    lead_status=existing.lead_status,
                    last_activity_at=_max_iso(existing.last_activity_at, last),
                    has_conversation=True,
                    has_appointments=existing.has_appointments,
                )

        for appt in appointments:
            phone = normalize_phone(appt.contact_phone)
            if not phone:
                continue
            existing = by_phone.get(phone)
            last = _iso(appt.starts_at)
            name = appt.contact_name or ""
            if existing is None:
                by_phone[phone] = ContactSummary(
                    phone=phone,
                    display_name=name or phone,
                    lead_status=None,
                    last_activity_at=last,
                    has_conversation=False,
                    has_appointments=True,
                )
            else:
                by_phone[phone] = ContactSummary(
                    phone=existing.phone,
                    display_name=existing.display_name
                    if existing.display_name != existing.phone
                    else (name or existing.display_name),
                    lead_status=existing.lead_status,
                    last_activity_at=_max_iso(existing.last_activity_at, last),
                    has_conversation=existing.has_conversation,
                    has_appointments=True,
                )

        now = self._now()
        enriched: list[ContactSummary] = []
        for c in by_phone.values():
            days = inactive_days_since(c.last_activity_at, now)
            enriched.append(
                ContactSummary(
                    phone=c.phone,
                    display_name=c.display_name,
                    lead_status=c.lead_status,
                    last_activity_at=c.last_activity_at,
                    has_conversation=c.has_conversation,
                    has_appointments=c.has_appointments,
                    inactive_days=days,
                )
            )

        if input.inactive_days_min is not None:
            min_days = max(0, input.inactive_days_min)
            enriched = [
                c
                for c in enriched
                if c.inactive_days is not None and c.inactive_days >= min_days
            ]

        items = sorted(
            enriched,
            key=lambda c: c.last_activity_at or "",
            reverse=True,
        )
        total = len(items)
        page = items[input.offset : input.offset + input.limit]
        return page, total
