"""Unit tests CRM-1: normalize phone + GetContact / ListContacts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.application.contact.get_contact import (
    GetContactInput,
    GetContactUseCase,
    ListContactsInput,
    ListContactsUseCase,
)
from app.domain.appointment.entity import Appointment, AppointmentStatus
from app.domain.conversation.entity import Conversation
from app.domain.lead.entity import Lead, LeadStatus
from app.domain.shared.errors import ContactNotFoundError
from app.domain.shared.phone import normalize_phone, phones_match
from tests.unit.appointment_fakes import FakeAppointmentRepository

CLIENT_UUID = uuid4()
CLIENT_ID = str(CLIENT_UUID)
PHONE = "+34600111222"


def test_normalize_phone_adds_plus() -> None:
    assert normalize_phone("34600111222") == "+34600111222"
    assert normalize_phone("+34 600 111 222") == "+34600111222"
    assert phones_match("34600111222", "+34600111222")


class FakeLeadRepo:
    def __init__(self) -> None:
        self.items: list[Lead] = []

    async def save(self, lead: Lead) -> None:
        self.items.append(lead)

    async def find_by_id(self, lead_id: str):
        return next((item for item in self.items if str(item.id) == lead_id), None)

    async def find_by_client_and_phone(self, client_id: str, phone: str):
        for lead in self.items:
            if str(lead.client_id) != client_id:
                continue
            if phones_match(lead.phone, phone) or lead.phone == phone:
                return lead
        return None

    async def list_by_client(self, client_id: str, status=None, limit=20, offset=0):
        items = [item for item in self.items if str(item.client_id) == client_id]
        return items[offset : offset + limit]

    async def count_by_client(self, client_id: str, status=None) -> int:
        return len([item for item in self.items if str(item.client_id) == client_id])

    async def get_stats(self, client_id: str) -> dict:
        return {}

    async def get_leads_new_today(self, client_id: str):
        return []


class FakeConversationRepo:
    def __init__(self) -> None:
        self.items: list[Conversation] = []

    async def list_by_client(self, client_id: str, limit=20, offset=0):
        items = [item for item in self.items if str(item.client_id) == client_id]
        return items[offset : offset + limit]

    async def count_by_client(self, client_id: str) -> int:
        return len([item for item in self.items if str(item.client_id) == client_id])

    async def get_messages(self, conversation_id: str):
        return []

    async def find_by_id(self, conversation_id: str):
        return next((item for item in self.items if str(item.id) == conversation_id), None)

    async def find_by_client_and_phone(self, client_id: str, phone: str):
        for conv in self.items:
            if str(conv.client_id) != client_id:
                continue
            if phones_match(conv.wa_phone_number, phone) or conv.wa_phone_number == phone:
                return conv
        return None

    async def save(self, conversation: Conversation) -> None:
        self.items.append(conversation)

    async def append_message(self, message) -> None:
        return None

    async def get_recent_messages(self, conversation_id: str, limit: int = 10):
        return []

    async def get_stats(self) -> dict:
        return {}


@pytest.mark.asyncio
async def test_get_contact_aggregates_lead_conversation_appointments() -> None:
    leads = FakeLeadRepo()
    convs = FakeConversationRepo()
    appts = FakeAppointmentRepository()

    await leads.save(
        Lead(
            client_id=CLIENT_UUID,
            phone=PHONE,
            name="María",
            status=LeadStatus.INTERESTED,
            score=80,
            notes="tinte",
        )
    )
    await convs.save(
        Conversation(
            client_id=CLIENT_UUID,
            wa_phone_number="34600111222",
            status="active",
        )
    )
    starts = datetime.now(timezone.utc) + timedelta(days=1)
    await appts.save(
        Appointment(
            client_id=CLIENT_UUID,
            contact_phone=PHONE,
            contact_name="María",
            starts_at=starts,
            ends_at=starts + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED,
        )
    )

    uc = GetContactUseCase(leads, convs, appts)
    detail = await uc.execute(GetContactInput(client_id=CLIENT_ID, phone="34600111222"))

    assert detail.phone == PHONE
    assert detail.display_name == "María"
    assert detail.lead is not None
    assert detail.lead.status == "interested"
    assert len(detail.conversations) == 1
    assert len(detail.appointments) == 1


@pytest.mark.asyncio
async def test_get_contact_not_found() -> None:
    uc = GetContactUseCase(FakeLeadRepo(), FakeConversationRepo(), FakeAppointmentRepository())
    with pytest.raises(ContactNotFoundError):
        await uc.execute(GetContactInput(client_id=CLIENT_ID, phone="+34999888777"))


@pytest.mark.asyncio
async def test_list_contacts_merges_sources() -> None:
    leads = FakeLeadRepo()
    convs = FakeConversationRepo()
    appts = FakeAppointmentRepository()

    await leads.save(
        Lead(client_id=CLIENT_UUID, phone="+34611111111", name="Ana", status=LeadStatus.NEW)
    )
    await convs.save(
        Conversation(client_id=CLIENT_UUID, wa_phone_number="+34622222222", status="active")
    )

    uc = ListContactsUseCase(leads, convs, appts)
    items, total = await uc.execute(ListContactsInput(client_id=CLIENT_ID, limit=50, offset=0))
    assert total == 2
    phones = {c.phone for c in items}
    assert "+34611111111" in phones
    assert "+34622222222" in phones
