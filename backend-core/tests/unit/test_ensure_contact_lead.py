"""Unit tests CRM-4 EnsureContactLeadUseCase."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.contact.ensure_contact_lead import (
    EnsureContactLeadInput,
    EnsureContactLeadUseCase,
)
from app.domain.lead.entity import Lead, LeadStatus
from app.domain.shared.errors import InvalidLeadError
from tests.unit.test_contact_use_cases import FakeLeadRepo

CLIENT_UUID = uuid4()
CLIENT_ID = str(CLIENT_UUID)
PHONE = "+34600111222"


@pytest.mark.asyncio
async def test_ensure_creates_lead_when_missing() -> None:
    repo = FakeLeadRepo()
    uc = EnsureContactLeadUseCase(repo)
    out = await uc.execute(
        EnsureContactLeadInput(
            client_id=CLIENT_ID,
            phone="34600111222",
            name="María",
            source="whatsapp",
        )
    )
    assert out.created is True
    assert out.phone == PHONE
    assert len(repo.items) == 1
    assert repo.items[0].source == "whatsapp"
    assert repo.items[0].last_contacted_at is not None


@pytest.mark.asyncio
async def test_ensure_is_idempotent() -> None:
    repo = FakeLeadRepo()
    uc = EnsureContactLeadUseCase(repo)
    first = await uc.execute(
        EnsureContactLeadInput(client_id=CLIENT_ID, phone=PHONE, source="appointment")
    )
    second = await uc.execute(
        EnsureContactLeadInput(
            client_id=CLIENT_ID, phone=PHONE, name="Ana", source="appointment"
        )
    )
    assert first.created is True
    assert second.created is False
    assert first.lead_id == second.lead_id
    assert len(repo.items) == 1
    assert repo.items[0].name == "Ana"


@pytest.mark.asyncio
async def test_ensure_does_not_overwrite_existing_name() -> None:
    repo = FakeLeadRepo()
    await repo.save(
        Lead(
            client_id=CLIENT_UUID,
            phone=PHONE,
            name="Original",
            status=LeadStatus.NEW,
            source="whatsapp",
        )
    )
    uc = EnsureContactLeadUseCase(repo)
    await uc.execute(
        EnsureContactLeadInput(
            client_id=CLIENT_ID, phone=PHONE, name="Otro", source="appointment"
        )
    )
    assert repo.items[0].name == "Original"


@pytest.mark.asyncio
async def test_ensure_rejects_empty_phone() -> None:
    uc = EnsureContactLeadUseCase(FakeLeadRepo())
    with pytest.raises(InvalidLeadError):
        await uc.execute(EnsureContactLeadInput(client_id=CLIENT_ID, phone=""))
