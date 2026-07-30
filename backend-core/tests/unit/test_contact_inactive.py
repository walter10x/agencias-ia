"""Unit tests CRM-5: inactive filter + mark contacted."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.contact.get_contact import (
    ListContactsInput,
    ListContactsUseCase,
    inactive_days_since,
)
from app.application.contact.mark_contact_contacted import (
    MarkContactContactedInput,
    MarkContactContactedUseCase,
)
from app.application.contact.get_contact import GetContactUseCase
from app.domain.lead.entity import Lead, LeadStatus
from tests.unit.appointment_fakes import FakeAppointmentRepository
from tests.unit.test_contact_use_cases import FakeConversationRepo, FakeLeadRepo

CLIENT_UUID = uuid4()
CLIENT_ID = str(CLIENT_UUID)
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def test_inactive_days_since() -> None:
    last = (NOW - timedelta(days=45)).isoformat()
    assert inactive_days_since(last, NOW) == 45
    assert inactive_days_since(None, NOW) is None


@pytest.mark.asyncio
async def test_list_contacts_filters_inactive() -> None:
    leads = FakeLeadRepo()
    await leads.save(
        Lead(
            client_id=CLIENT_UUID,
            phone="+34611111111",
            name="Viejo",
            status=LeadStatus.NEW,
            updated_at=NOW - timedelta(days=90),
        )
    )
    await leads.save(
        Lead(
            client_id=CLIENT_UUID,
            phone="+34622222222",
            name="Reciente",
            status=LeadStatus.NEW,
            updated_at=NOW - timedelta(days=5),
        )
    )
    uc = ListContactsUseCase(
        leads,
        FakeConversationRepo(),
        FakeAppointmentRepository(),
        now_provider=lambda: NOW,
    )
    items, total = await uc.execute(
        ListContactsInput(client_id=CLIENT_ID, inactive_days_min=60)
    )
    assert total == 1
    assert items[0].phone == "+34611111111"
    assert items[0].inactive_days is not None
    assert items[0].inactive_days >= 60


@pytest.mark.asyncio
async def test_mark_contact_contacted() -> None:
    leads = FakeLeadRepo()
    get_uc = GetContactUseCase(leads, FakeConversationRepo(), FakeAppointmentRepository())
    uc = MarkContactContactedUseCase(leads, get_uc)
    detail = await uc.execute(
        MarkContactContactedInput(client_id=CLIENT_ID, phone="+34600111222")
    )
    assert detail.lead is not None
    assert detail.lead.status == "contacted"
    assert leads.items[0].last_contacted_at is not None
