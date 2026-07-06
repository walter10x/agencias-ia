"""Unit tests de reglas de dominio del módulo de agenda.

Cubre: invariantes de Appointment, transiciones de estado, solapamiento,
horario del negocio (BusinessSchedule) y la regla de "no en el pasado".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.appointment.entity import (
    Appointment,
    AppointmentStatus,
    BusinessSchedule,
    ensure_not_in_past,
)
from app.domain.shared.errors import InvalidAppointmentError

# Lunes 2030-01-07 — fecha futura y estable para los tests
MONDAY_10 = datetime(2030, 1, 7, 10, 0, tzinfo=timezone.utc)
MONDAY_11 = datetime(2030, 1, 7, 11, 0, tzinfo=timezone.utc)


def _make_appointment(**overrides) -> Appointment:
    defaults = dict(
        client_id=uuid4(),
        contact_phone="584121234567",
        contact_name="Ana",
        starts_at=MONDAY_10,
        ends_at=MONDAY_10 + timedelta(minutes=30),
    )
    defaults.update(overrides)
    return Appointment(**defaults)


# ============================================================================
# Invariantes de la entidad
# ============================================================================


class TestAppointmentInvariants:
    def test_creates_with_pending_status_by_default(self) -> None:
        appt = _make_appointment()
        assert appt.status == AppointmentStatus.PENDING
        assert appt.reminder_sent_at is None

    def test_empty_phone_raises(self) -> None:
        with pytest.raises(InvalidAppointmentError, match="contact_phone"):
            _make_appointment(contact_phone="   ")

    def test_ends_before_start_raises(self) -> None:
        with pytest.raises(InvalidAppointmentError, match="ends_at"):
            _make_appointment(ends_at=MONDAY_10 - timedelta(minutes=30))

    def test_ends_equal_start_raises(self) -> None:
        with pytest.raises(InvalidAppointmentError, match="ends_at"):
            _make_appointment(ends_at=MONDAY_10)

    def test_string_status_is_coerced_to_enum(self) -> None:
        appt = _make_appointment(status="confirmed")
        assert appt.status == AppointmentStatus.CONFIRMED

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(InvalidAppointmentError, match="Invalid status"):
            _make_appointment(status="no_show")


# ============================================================================
# Solapamiento
# ============================================================================


class TestOverlap:
    def test_overlapping_ranges_detected(self) -> None:
        appt = _make_appointment()
        assert appt.overlaps_range(
            MONDAY_10 + timedelta(minutes=15), MONDAY_10 + timedelta(minutes=45)
        )

    def test_containing_range_detected(self) -> None:
        appt = _make_appointment()
        assert appt.overlaps_range(
            MONDAY_10 - timedelta(hours=1), MONDAY_10 + timedelta(hours=2)
        )

    def test_back_to_back_does_not_overlap(self) -> None:
        """Una cita que empieza exactamente cuando termina otra NO solapa."""
        appt = _make_appointment()
        assert not appt.overlaps_range(
            MONDAY_10 + timedelta(minutes=30), MONDAY_10 + timedelta(minutes=60)
        )
        assert not appt.overlaps_range(
            MONDAY_10 - timedelta(minutes=30), MONDAY_10
        )

    def test_cancelled_appointment_does_not_block(self) -> None:
        appt = _make_appointment()
        appt.cancel()
        assert not appt.overlaps_range(MONDAY_10, MONDAY_10 + timedelta(minutes=30))

    def test_completed_appointment_does_not_block(self) -> None:
        appt = _make_appointment()
        appt.complete()
        assert not appt.overlaps_range(MONDAY_10, MONDAY_10 + timedelta(minutes=30))

    def test_overlaps_between_entities_requires_same_client(self) -> None:
        a = _make_appointment()
        b = _make_appointment()  # otro client_id
        assert not a.overlaps(b)

    def test_overlaps_between_entities_same_client(self) -> None:
        client_id = uuid4()
        a = _make_appointment(client_id=client_id)
        b = _make_appointment(
            client_id=client_id,
            starts_at=MONDAY_10 + timedelta(minutes=15),
            ends_at=MONDAY_10 + timedelta(minutes=45),
        )
        assert a.overlaps(b)


# ============================================================================
# Transiciones de estado
# ============================================================================


class TestStatusTransitions:
    def test_confirm_pending(self) -> None:
        appt = _make_appointment()
        appt.confirm()
        assert appt.status == AppointmentStatus.CONFIRMED

    def test_confirm_twice_raises(self) -> None:
        appt = _make_appointment()
        appt.confirm()
        with pytest.raises(InvalidAppointmentError):
            appt.confirm()

    def test_cancel_pending(self) -> None:
        appt = _make_appointment()
        appt.cancel()
        assert appt.status == AppointmentStatus.CANCELLED

    def test_cancel_twice_raises(self) -> None:
        appt = _make_appointment()
        appt.cancel()
        with pytest.raises(InvalidAppointmentError, match="already cancelled"):
            appt.cancel()

    def test_cancel_completed_raises(self) -> None:
        appt = _make_appointment()
        appt.complete()
        with pytest.raises(InvalidAppointmentError, match="completed"):
            appt.cancel()

    def test_complete_cancelled_raises(self) -> None:
        appt = _make_appointment()
        appt.cancel()
        with pytest.raises(InvalidAppointmentError):
            appt.complete()

    def test_reschedule_updates_range_and_resets_reminder(self) -> None:
        appt = _make_appointment()
        appt.mark_reminder_sent()
        assert appt.reminder_sent_at is not None

        appt.reschedule(MONDAY_11, MONDAY_11 + timedelta(minutes=30))

        assert appt.starts_at == MONDAY_11
        assert appt.ends_at == MONDAY_11 + timedelta(minutes=30)
        assert appt.reminder_sent_at is None

    def test_reschedule_cancelled_raises(self) -> None:
        appt = _make_appointment()
        appt.cancel()
        with pytest.raises(InvalidAppointmentError, match="cancelled"):
            appt.reschedule(MONDAY_11, MONDAY_11 + timedelta(minutes=30))

    def test_reschedule_invalid_range_raises(self) -> None:
        appt = _make_appointment()
        with pytest.raises(InvalidAppointmentError, match="ends_at"):
            appt.reschedule(MONDAY_11, MONDAY_11)


# ============================================================================
# No en el pasado
# ============================================================================


class TestEnsureNotInPast:
    def test_past_raises(self) -> None:
        now = MONDAY_10
        with pytest.raises(InvalidAppointmentError, match="past"):
            ensure_not_in_past(now - timedelta(minutes=1), now=now)

    def test_future_ok(self) -> None:
        now = MONDAY_10
        ensure_not_in_past(now + timedelta(minutes=1), now=now)

    def test_exactly_now_ok(self) -> None:
        now = MONDAY_10
        ensure_not_in_past(now, now=now)


# ============================================================================
# BusinessSchedule — horario del negocio
# ============================================================================


class TestBusinessSchedule:
    def test_default_covers_weekday_working_hours(self) -> None:
        schedule = BusinessSchedule.default()
        assert schedule.covers(MONDAY_10, MONDAY_10 + timedelta(minutes=30))

    def test_does_not_cover_before_opening(self) -> None:
        schedule = BusinessSchedule.default()
        early = MONDAY_10.replace(hour=8, minute=30)
        assert not schedule.covers(early, early + timedelta(minutes=30))

    def test_does_not_cover_after_closing(self) -> None:
        schedule = BusinessSchedule.default()
        late = MONDAY_10.replace(hour=17, minute=45)
        # Termina 18:15, fuera del rango 09:00-18:00
        assert not schedule.covers(late, late + timedelta(minutes=30))

    def test_covers_slot_ending_exactly_at_closing(self) -> None:
        schedule = BusinessSchedule.default()
        last = MONDAY_10.replace(hour=17, minute=30)
        assert schedule.covers(last, last + timedelta(minutes=30))

    def test_closed_day_not_covered(self) -> None:
        schedule = BusinessSchedule.default()
        sunday = datetime(2030, 1, 6, 10, 0, tzinfo=timezone.utc)  # domingo
        assert not schedule.covers(sunday, sunday + timedelta(minutes=30))

    def test_appointment_crossing_midnight_not_covered(self) -> None:
        schedule = BusinessSchedule(
            weekly_hours={"monday": [("09:00", "23:00")]},
        )
        night = datetime(2030, 1, 7, 23, 30, tzinfo=timezone.utc)
        assert not schedule.covers(night, night + timedelta(hours=1))

    def test_multiple_ranges_per_day(self) -> None:
        schedule = BusinessSchedule(
            weekly_hours={"monday": [("09:00", "13:00"), ("15:00", "19:00")]},
        )
        morning = MONDAY_10
        siesta = MONDAY_10.replace(hour=13, minute=30)
        afternoon = MONDAY_10.replace(hour=16)
        assert schedule.covers(morning, morning + timedelta(minutes=30))
        assert not schedule.covers(siesta, siesta + timedelta(minutes=30))
        assert schedule.covers(afternoon, afternoon + timedelta(minutes=30))

    def test_respects_business_timezone(self) -> None:
        """14:00 UTC = 10:00 en America/Caracas (-04:00) → dentro de horario."""
        schedule = BusinessSchedule(timezone="America/Caracas")
        utc_dt = datetime(2030, 1, 7, 14, 0, tzinfo=timezone.utc)
        assert schedule.covers(utc_dt, utc_dt + timedelta(minutes=30))
        # 23:00 UTC = 19:00 local → fuera
        late = datetime(2030, 1, 7, 23, 0, tzinfo=timezone.utc)
        assert not schedule.covers(late, late + timedelta(minutes=30))

    def test_invalid_time_format_raises(self) -> None:
        schedule = BusinessSchedule(weekly_hours={"monday": [("9am", "18:00")]})
        with pytest.raises(InvalidAppointmentError, match="Invalid time format"):
            schedule.ranges_for(MONDAY_10.date())

    def test_inverted_range_raises(self) -> None:
        schedule = BusinessSchedule(weekly_hours={"monday": [("18:00", "09:00")]})
        with pytest.raises(InvalidAppointmentError, match="Invalid business hours"):
            schedule.ranges_for(MONDAY_10.date())

    def test_invalid_duration_raises(self) -> None:
        with pytest.raises(InvalidAppointmentError, match="duration"):
            BusinessSchedule(appointment_duration_minutes=0)

    def test_invalid_timezone_raises(self) -> None:
        with pytest.raises(InvalidAppointmentError, match="timezone"):
            BusinessSchedule(timezone="Marte/Olympus")

    # ------------------------------------------------------------------
    # reminder_offset_minutes (Fase 4)
    # ------------------------------------------------------------------

    def test_default_reminder_offset_is_24h(self) -> None:
        schedule = BusinessSchedule.default()
        assert schedule.reminder_offset_minutes == 1440

    def test_custom_reminder_offset(self) -> None:
        schedule = BusinessSchedule(reminder_offset_minutes=60)
        assert schedule.reminder_offset_minutes == 60

    def test_negative_reminder_offset_raises(self) -> None:
        with pytest.raises(InvalidAppointmentError, match="reminder_offset_minutes"):
            BusinessSchedule(reminder_offset_minutes=-1)
