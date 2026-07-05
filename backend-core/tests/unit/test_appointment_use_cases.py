"""Unit tests de los use cases del módulo de agenda (repos in-memory)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.application.appointment.cancel_appointment import CancelAppointmentUseCase
from app.application.appointment.create_appointment import CreateAppointmentUseCase
from app.application.appointment.get_availability import GetAvailabilityUseCase
from app.application.appointment.list_appointments import ListAppointmentsUseCase
from app.application.appointment.reschedule_appointment import (
    RescheduleAppointmentUseCase,
)
from app.application.dtos import (
    CancelAppointmentInput,
    CreateAppointmentInput,
    GetAvailabilityInput,
    ListAppointmentsInput,
    RescheduleAppointmentInput,
)
from app.domain.appointment.entity import Appointment, BusinessSchedule
from app.domain.shared.errors import (
    AppointmentNotFoundError,
    AppointmentOverlapError,
    InvalidAppointmentError,
    OutsideBusinessHoursError,
)
from tests.unit.appointment_fakes import (
    FakeAppointmentRepository,
    FakeScheduleRepository,
)

CLIENT_ID = str(uuid4())
OTHER_CLIENT_ID = str(uuid4())

# Lunes 2030-01-07 — futuro estable
MONDAY = datetime(2030, 1, 7, tzinfo=timezone.utc)
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def _now() -> datetime:
    return NOW


def _make_use_case(repo=None, schedule=None):
    repo = repo or FakeAppointmentRepository()
    schedule_repo = FakeScheduleRepository(schedule)
    return (
        CreateAppointmentUseCase(repo=repo, schedule_repo=schedule_repo, now_provider=_now),
        repo,
        schedule_repo,
    )


def _create_input(**overrides) -> CreateAppointmentInput:
    defaults = dict(
        client_id=CLIENT_ID,
        starts_at="2030-01-07T10:00:00+00:00",
        contact_phone="584121234567",
        contact_name="Ana",
    )
    defaults.update(overrides)
    return CreateAppointmentInput(**defaults)


async def _seed_appointment(repo, **overrides) -> Appointment:
    defaults = dict(
        client_id=uuid4(),
        contact_phone="584121234567",
        contact_name="Ana",
        starts_at=MONDAY.replace(hour=10),
        ends_at=MONDAY.replace(hour=10, minute=30),
    )
    defaults.update(overrides)
    appt = Appointment(**defaults)
    await repo.save(appt)
    return appt


# ============================================================================
# CreateAppointmentUseCase
# ============================================================================


class TestCreateAppointment:
    @pytest.mark.asyncio
    async def test_creates_appointment_with_default_duration(self) -> None:
        uc, repo, _ = _make_use_case()

        output = await uc.execute(_create_input())

        assert output.status == "pending"
        assert output.client_id == CLIENT_ID
        saved = repo.items[output.id]
        assert saved.ends_at - saved.starts_at == timedelta(minutes=30)

    @pytest.mark.asyncio
    async def test_naive_datetime_interpreted_in_business_timezone(self) -> None:
        schedule = BusinessSchedule(timezone="America/Caracas")
        uc, repo, _ = _make_use_case(schedule=schedule)

        output = await uc.execute(_create_input(starts_at="2030-01-07T10:00"))

        saved = repo.items[output.id]
        # 10:00 en Caracas (-04:00) == 14:00 UTC
        assert saved.starts_at == datetime(2030, 1, 7, 14, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_past_appointment_raises(self) -> None:
        uc, _, _ = _make_use_case()
        with pytest.raises(InvalidAppointmentError, match="past"):
            await uc.execute(_create_input(starts_at="2029-12-31T10:00:00+00:00"))

    @pytest.mark.asyncio
    async def test_outside_business_hours_raises(self) -> None:
        uc, _, _ = _make_use_case()
        with pytest.raises(OutsideBusinessHoursError):
            await uc.execute(_create_input(starts_at="2030-01-07T20:00:00+00:00"))

    @pytest.mark.asyncio
    async def test_closed_day_raises(self) -> None:
        uc, _, _ = _make_use_case()
        with pytest.raises(OutsideBusinessHoursError):
            # 2030-01-06 es domingo
            await uc.execute(_create_input(starts_at="2030-01-06T10:00:00+00:00"))

    @pytest.mark.asyncio
    async def test_overlapping_appointment_raises(self) -> None:
        uc, repo, _ = _make_use_case()
        await _seed_appointment(repo, client_id=UUID(CLIENT_ID))

        with pytest.raises(AppointmentOverlapError):
            await uc.execute(_create_input(starts_at="2030-01-07T10:15:00+00:00"))

    @pytest.mark.asyncio
    async def test_cancelled_appointment_does_not_block_slot(self) -> None:
        uc, repo, _ = _make_use_case()
        blocked = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        blocked.cancel()

        output = await uc.execute(_create_input(starts_at="2030-01-07T10:00:00+00:00"))
        assert output.status == "pending"

    @pytest.mark.asyncio
    async def test_back_to_back_appointment_allowed(self) -> None:
        uc, repo, _ = _make_use_case()
        await _seed_appointment(repo, client_id=UUID(CLIENT_ID))

        output = await uc.execute(_create_input(starts_at="2030-01-07T10:30:00+00:00"))
        assert output.starts_at == "2030-01-07T10:30:00+00:00"

    @pytest.mark.asyncio
    async def test_other_tenant_appointment_does_not_block(self) -> None:
        """Aislamiento multi-tenant: las citas de otro negocio no bloquean."""
        uc, repo, _ = _make_use_case()
        await _seed_appointment(repo)  # client_id aleatorio (otro tenant)

        output = await uc.execute(_create_input(starts_at="2030-01-07T10:00:00+00:00"))
        assert output.status == "pending"

    @pytest.mark.asyncio
    async def test_missing_phone_raises(self) -> None:
        uc, _, _ = _make_use_case()
        with pytest.raises(InvalidAppointmentError, match="contact_phone"):
            await uc.execute(_create_input(contact_phone="  "))

    @pytest.mark.asyncio
    async def test_invalid_datetime_format_raises(self) -> None:
        uc, _, _ = _make_use_case()
        with pytest.raises(InvalidAppointmentError, match="format"):
            await uc.execute(_create_input(starts_at="mañana a las 10"))


# ============================================================================
# CancelAppointmentUseCase
# ============================================================================


class TestCancelAppointment:
    @pytest.mark.asyncio
    async def test_cancels_own_appointment(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        uc = CancelAppointmentUseCase(repo=repo)

        output = await uc.execute(
            CancelAppointmentInput(client_id=CLIENT_ID, appointment_id=str(appt.id))
        )

        assert output.status == "cancelled"
        assert repo.items[str(appt.id)].status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_unknown_id_raises_not_found(self) -> None:
        uc = CancelAppointmentUseCase(repo=FakeAppointmentRepository())
        with pytest.raises(AppointmentNotFoundError):
            await uc.execute(
                CancelAppointmentInput(client_id=CLIENT_ID, appointment_id=str(uuid4()))
            )

    @pytest.mark.asyncio
    async def test_cancel_other_tenant_appointment_raises_not_found(self) -> None:
        """Aislamiento: el tenant B no puede cancelar citas del tenant A."""
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        uc = CancelAppointmentUseCase(repo=repo)

        with pytest.raises(AppointmentNotFoundError):
            await uc.execute(
                CancelAppointmentInput(
                    client_id=OTHER_CLIENT_ID, appointment_id=str(appt.id)
                )
            )
        assert repo.items[str(appt.id)].status.value == "pending"

    @pytest.mark.asyncio
    async def test_cancel_twice_raises_invalid(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        uc = CancelAppointmentUseCase(repo=repo)
        dto = CancelAppointmentInput(client_id=CLIENT_ID, appointment_id=str(appt.id))

        await uc.execute(dto)
        with pytest.raises(InvalidAppointmentError, match="already cancelled"):
            await uc.execute(dto)


# ============================================================================
# RescheduleAppointmentUseCase
# ============================================================================


class TestRescheduleAppointment:
    def _uc(self, repo):
        return RescheduleAppointmentUseCase(
            repo=repo,
            schedule_repo=FakeScheduleRepository(),
            now_provider=_now,
        )

    @pytest.mark.asyncio
    async def test_reschedule_keeps_duration(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(
            repo,
            client_id=UUID(CLIENT_ID),
            ends_at=MONDAY.replace(hour=11),  # 1h de duración
        )
        uc = self._uc(repo)

        output = await uc.execute(
            RescheduleAppointmentInput(
                client_id=CLIENT_ID,
                appointment_id=str(appt.id),
                new_starts_at="2030-01-07T14:00:00+00:00",
            )
        )

        assert output.starts_at == "2030-01-07T14:00:00+00:00"
        assert output.ends_at == "2030-01-07T15:00:00+00:00"

    @pytest.mark.asyncio
    async def test_reschedule_does_not_collide_with_itself(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        uc = self._uc(repo)

        # Mover 15 min: el nuevo rango solapa con el rango viejo de la MISMA cita
        output = await uc.execute(
            RescheduleAppointmentInput(
                client_id=CLIENT_ID,
                appointment_id=str(appt.id),
                new_starts_at="2030-01-07T10:15:00+00:00",
            )
        )
        assert output.starts_at == "2030-01-07T10:15:00+00:00"

    @pytest.mark.asyncio
    async def test_reschedule_into_another_appointment_raises(self) -> None:
        repo = FakeAppointmentRepository()
        client_uuid = UUID(CLIENT_ID)
        appt = await _seed_appointment(repo, client_id=client_uuid)
        await _seed_appointment(
            repo,
            client_id=client_uuid,
            starts_at=MONDAY.replace(hour=14),
            ends_at=MONDAY.replace(hour=14, minute=30),
        )
        uc = self._uc(repo)

        with pytest.raises(AppointmentOverlapError):
            await uc.execute(
                RescheduleAppointmentInput(
                    client_id=CLIENT_ID,
                    appointment_id=str(appt.id),
                    new_starts_at="2030-01-07T14:15:00+00:00",
                )
            )

    @pytest.mark.asyncio
    async def test_reschedule_outside_hours_raises(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        uc = self._uc(repo)

        with pytest.raises(OutsideBusinessHoursError):
            await uc.execute(
                RescheduleAppointmentInput(
                    client_id=CLIENT_ID,
                    appointment_id=str(appt.id),
                    new_starts_at="2030-01-07T22:00:00+00:00",
                )
            )

    @pytest.mark.asyncio
    async def test_reschedule_other_tenant_raises_not_found(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        uc = self._uc(repo)

        with pytest.raises(AppointmentNotFoundError):
            await uc.execute(
                RescheduleAppointmentInput(
                    client_id=OTHER_CLIENT_ID,
                    appointment_id=str(appt.id),
                    new_starts_at="2030-01-07T14:00:00+00:00",
                )
            )

    @pytest.mark.asyncio
    async def test_reschedule_cancelled_raises(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        appt.cancel()
        uc = self._uc(repo)

        with pytest.raises(InvalidAppointmentError, match="cancelled"):
            await uc.execute(
                RescheduleAppointmentInput(
                    client_id=CLIENT_ID,
                    appointment_id=str(appt.id),
                    new_starts_at="2030-01-07T14:00:00+00:00",
                )
            )


# ============================================================================
# ListAppointmentsUseCase
# ============================================================================


class TestListAppointments:
    @pytest.mark.asyncio
    async def test_lists_only_own_appointments(self) -> None:
        repo = FakeAppointmentRepository()
        client_uuid = UUID(CLIENT_ID)
        await _seed_appointment(repo, client_id=client_uuid)
        await _seed_appointment(repo)  # otro tenant
        uc = ListAppointmentsUseCase(repo=repo, schedule_repo=FakeScheduleRepository())

        outputs, total = await uc.execute(ListAppointmentsInput(client_id=CLIENT_ID))

        assert total == 1
        assert len(outputs) == 1
        assert outputs[0].client_id == CLIENT_ID

    @pytest.mark.asyncio
    async def test_filters_by_status(self) -> None:
        repo = FakeAppointmentRepository()
        client_uuid = UUID(CLIENT_ID)
        active = await _seed_appointment(repo, client_id=client_uuid)
        cancelled = await _seed_appointment(
            repo,
            client_id=client_uuid,
            starts_at=MONDAY.replace(hour=14),
            ends_at=MONDAY.replace(hour=14, minute=30),
        )
        cancelled.cancel()
        uc = ListAppointmentsUseCase(repo=repo, schedule_repo=FakeScheduleRepository())

        outputs, total = await uc.execute(
            ListAppointmentsInput(client_id=CLIENT_ID, status="cancelled")
        )

        assert total == 1
        assert outputs[0].id == str(cancelled.id)
        assert outputs[0].id != str(active.id)

    @pytest.mark.asyncio
    async def test_filters_by_date_range(self) -> None:
        repo = FakeAppointmentRepository()
        client_uuid = UUID(CLIENT_ID)
        monday_appt = await _seed_appointment(repo, client_id=client_uuid)
        await _seed_appointment(
            repo,
            client_id=client_uuid,
            starts_at=MONDAY + timedelta(days=7, hours=10),
            ends_at=MONDAY + timedelta(days=7, hours=10, minutes=30),
        )
        uc = ListAppointmentsUseCase(repo=repo, schedule_repo=FakeScheduleRepository())

        outputs, total = await uc.execute(
            ListAppointmentsInput(
                client_id=CLIENT_ID,
                date_from="2030-01-07",
                date_to="2030-01-07",
            )
        )

        assert total == 1
        assert outputs[0].id == str(monday_appt.id)

    @pytest.mark.asyncio
    async def test_invalid_status_raises(self) -> None:
        uc = ListAppointmentsUseCase(
            repo=FakeAppointmentRepository(), schedule_repo=FakeScheduleRepository()
        )
        with pytest.raises(InvalidAppointmentError, match="Invalid status"):
            await uc.execute(ListAppointmentsInput(client_id=CLIENT_ID, status="foo"))


# ============================================================================
# GetAvailabilityUseCase
# ============================================================================


class TestGetAvailability:
    def _uc(self, repo=None, schedule=None, now=None):
        return GetAvailabilityUseCase(
            repo=repo or FakeAppointmentRepository(),
            schedule_repo=FakeScheduleRepository(schedule),
            now_provider=(lambda: now) if now else _now,
        )

    @pytest.mark.asyncio
    async def test_open_day_generates_all_slots(self) -> None:
        uc = self._uc()

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-07")
        )

        # 09:00-18:00 con slots de 30 min = 18 slots
        assert len(output.slots) == 18
        assert output.slots[0].label == "09:00"
        assert output.slots[-1].label == "17:30"
        assert output.slot_duration_minutes == 30

    @pytest.mark.asyncio
    async def test_closed_day_has_no_slots(self) -> None:
        uc = self._uc()

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-06")  # domingo
        )

        assert output.slots == []

    @pytest.mark.asyncio
    async def test_booked_slot_excluded(self) -> None:
        repo = FakeAppointmentRepository()
        await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        uc = self._uc(repo=repo)

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-07")
        )

        labels = [s.label for s in output.slots]
        assert "10:00" not in labels
        assert "10:30" in labels
        assert len(output.slots) == 17

    @pytest.mark.asyncio
    async def test_cancelled_appointment_frees_slot(self) -> None:
        repo = FakeAppointmentRepository()
        appt = await _seed_appointment(repo, client_id=UUID(CLIENT_ID))
        appt.cancel()
        uc = self._uc(repo=repo)

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-07")
        )

        assert "10:00" in [s.label for s in output.slots]

    @pytest.mark.asyncio
    async def test_other_tenant_booking_does_not_affect_slots(self) -> None:
        repo = FakeAppointmentRepository()
        await _seed_appointment(repo)  # otro tenant a las 10:00
        uc = self._uc(repo=repo)

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-07")
        )

        assert "10:00" in [s.label for s in output.slots]

    @pytest.mark.asyncio
    async def test_past_slots_excluded_for_today(self) -> None:
        # "Hoy" es lunes 2030-01-07 a las 12:10 UTC
        now = datetime(2030, 1, 7, 12, 10, tzinfo=timezone.utc)
        uc = self._uc(now=now)

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-07")
        )

        labels = [s.label for s in output.slots]
        assert "12:00" not in labels
        assert labels[0] == "12:30"

    @pytest.mark.asyncio
    async def test_respects_custom_duration_and_ranges(self) -> None:
        schedule = BusinessSchedule(
            weekly_hours={"monday": [("09:00", "12:00")]},
            appointment_duration_minutes=60,
        )
        uc = self._uc(schedule=schedule)

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-07")
        )

        assert [s.label for s in output.slots] == ["09:00", "10:00", "11:00"]

    @pytest.mark.asyncio
    async def test_slots_are_utc_isoformat_in_business_timezone(self) -> None:
        schedule = BusinessSchedule(
            weekly_hours={"monday": [("09:00", "10:00")]},
            timezone="America/Caracas",
        )
        uc = self._uc(schedule=schedule)

        output = await uc.execute(
            GetAvailabilityInput(client_id=CLIENT_ID, date="2030-01-07")
        )

        # 09:00 Caracas == 13:00 UTC
        assert output.slots[0].label == "09:00"
        assert output.slots[0].starts_at == datetime(
            2030, 1, 7, 13, 0, tzinfo=timezone.utc
        ).isoformat()
        assert output.timezone == "America/Caracas"

    @pytest.mark.asyncio
    async def test_invalid_date_raises(self) -> None:
        uc = self._uc()
        with pytest.raises(InvalidAppointmentError, match="date"):
            await uc.execute(GetAvailabilityInput(client_id=CLIENT_ID, date="7/1/2030"))
