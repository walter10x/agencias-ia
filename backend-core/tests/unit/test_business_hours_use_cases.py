"""Unit tests UpdateBusinessHoursUseCase / GetBusinessHoursUseCase."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.appointment.get_business_hours import (
    GetBusinessHoursInput,
    GetBusinessHoursUseCase,
)
from app.application.appointment.update_business_hours import (
    UpdateBusinessHoursInput,
    UpdateBusinessHoursUseCase,
)
from app.domain.appointment.entity import BusinessSchedule
from app.domain.shared.errors import ClientNotFoundError, InvalidAppointmentError
from tests.unit.appointment_fakes import FakeScheduleRepository

CLIENT_ID = str(uuid4())


@pytest.mark.asyncio
async def test_get_business_hours_returns_defaults() -> None:
    repo = FakeScheduleRepository(BusinessSchedule.default())
    uc = GetBusinessHoursUseCase(repo)
    out = await uc.execute(GetBusinessHoursInput(client_id=CLIENT_ID))
    assert out.timezone == "UTC"
    assert out.appointment_duration_minutes == 30
    assert "monday" in out.weekly


@pytest.mark.asyncio
async def test_update_business_hours_persists() -> None:
    repo = FakeScheduleRepository(BusinessSchedule.default())
    uc = UpdateBusinessHoursUseCase(repo)
    out = await uc.execute(
        UpdateBusinessHoursInput(
            client_id=CLIENT_ID,
            timezone="Europe/Madrid",
            appointment_duration_minutes=45,
            reminder_offset_minutes=60,
            weekly={
                "monday": [["10:00", "14:00"]],
                "tuesday": [],
                "wednesday": [["10:00", "18:00"]],
                "thursday": [],
                "friday": [],
                "saturday": [],
                "sunday": [],
            },
        )
    )
    assert out.timezone == "Europe/Madrid"
    assert out.appointment_duration_minutes == 45
    assert out.weekly["monday"] == [["10:00", "14:00"]]
    assert out.weekly["tuesday"] == []
    saved = await repo.get_business_schedule(CLIENT_ID)
    assert saved is not None
    assert saved.timezone == "Europe/Madrid"


@pytest.mark.asyncio
async def test_update_rejects_bad_duration() -> None:
    repo = FakeScheduleRepository(BusinessSchedule.default())
    uc = UpdateBusinessHoursUseCase(repo)
    with pytest.raises(InvalidAppointmentError):
        await uc.execute(
            UpdateBusinessHoursInput(
                client_id=CLIENT_ID,
                timezone="UTC",
                appointment_duration_minutes=1,
                weekly={"monday": [["09:00", "18:00"]]},
            )
        )


@pytest.mark.asyncio
async def test_update_missing_client_raises() -> None:
    repo = FakeScheduleRepository(by_client={CLIENT_ID: None})
    # get returns None for this client_id when in by_client as None
    repo.by_client[CLIENT_ID] = None  # type: ignore[assignment]
    # Fake returns by_client value even if None — but get_business_schedule returns None
    # Need schedule that makes get return None: put None in by_client
    uc = UpdateBusinessHoursUseCase(repo)
    with pytest.raises(ClientNotFoundError):
        await uc.execute(
            UpdateBusinessHoursInput(
                client_id=CLIENT_ID,
                timezone="UTC",
                appointment_duration_minutes=30,
                weekly={},
            )
        )
