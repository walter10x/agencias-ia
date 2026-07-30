"""Unit test: CreateAppointmentUseCase asegura lead (CRM-4) cuando hay lead_repo."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.appointment.create_appointment import CreateAppointmentUseCase
from app.application.dtos import CreateAppointmentInput
from app.domain.appointment.entity import BusinessSchedule
from app.domain.shared.phone import normalize_phone
from tests.unit.appointment_fakes import FakeAppointmentRepository, FakeScheduleRepository
from tests.unit.test_contact_use_cases import FakeLeadRepo

CLIENT_ID = str(uuid4())


@pytest.mark.asyncio
async def test_create_appointment_ensures_lead() -> None:
    appt_repo = FakeAppointmentRepository()
    schedule = BusinessSchedule.default()
    # Abrir un día futuro seguro: usar starts lejos
    starts = datetime(2030, 1, 7, 10, 0, tzinfo=timezone.utc)  # monday
    leads = FakeLeadRepo()

    uc = CreateAppointmentUseCase(
        repo=appt_repo,
        schedule_repo=FakeScheduleRepository(schedule),
        lead_repo=leads,
        now_provider=lambda: datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    await uc.execute(
        CreateAppointmentInput(
            client_id=CLIENT_ID,
            starts_at=starts.isoformat(),
            contact_phone="34600111222",
            contact_name="María",
        )
    )
    assert len(leads.items) == 1
    assert leads.items[0].phone == normalize_phone("34600111222")
    assert leads.items[0].source == "appointment"
    assert leads.items[0].name == "María"
