"""Unit tests CRM-3 UpdateContactNotesUseCase."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.contact.get_contact import GetContactUseCase
from app.application.contact.update_contact_notes import (
    UpdateContactNotesInput,
    UpdateContactNotesUseCase,
)
from app.domain.shared.errors import InvalidLeadError
from tests.unit.appointment_fakes import FakeAppointmentRepository
from tests.unit.test_contact_use_cases import FakeConversationRepo, FakeLeadRepo

CLIENT_UUID = uuid4()
CLIENT_ID = str(CLIENT_UUID)
PHONE = "+34600111222"


def _uc() -> tuple[UpdateContactNotesUseCase, FakeLeadRepo]:
    leads = FakeLeadRepo()
    get_contact = GetContactUseCase(leads, FakeConversationRepo(), FakeAppointmentRepository())
    return UpdateContactNotesUseCase(leads, get_contact), leads


@pytest.mark.asyncio
async def test_update_notes_creates_lead_when_missing() -> None:
    uc, leads = _uc()
    detail = await uc.execute(
        UpdateContactNotesInput(
            client_id=CLIENT_ID,
            phone="34600111222",
            notes="Prefiere martes",
            display_name="María",
        )
    )
    assert detail.phone == PHONE
    assert detail.display_name == "María"
    assert detail.lead is not None
    assert detail.lead.notes == "Prefiere martes"
    assert len(leads.items) == 1
    assert leads.items[0].source == "manual"


@pytest.mark.asyncio
async def test_update_notes_updates_existing_lead() -> None:
    from app.domain.lead.entity import Lead, LeadStatus

    uc, leads = _uc()
    await leads.save(
        Lead(
            client_id=CLIENT_UUID,
            phone=PHONE,
            name="Ana",
            status=LeadStatus.INTERESTED,
            notes="viejo",
        )
    )
    detail = await uc.execute(
        UpdateContactNotesInput(client_id=CLIENT_ID, phone=PHONE, notes="nuevo")
    )
    assert detail.lead is not None
    assert detail.lead.notes == "nuevo"
    assert detail.lead.name == "Ana"
    assert len(leads.items) == 1


@pytest.mark.asyncio
async def test_update_notes_rejects_too_long() -> None:
    uc, _ = _uc()
    with pytest.raises(InvalidLeadError):
        await uc.execute(
            UpdateContactNotesInput(
                client_id=CLIENT_ID,
                phone=PHONE,
                notes="x" * 5001,
            )
        )
