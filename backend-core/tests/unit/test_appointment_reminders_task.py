"""Unit tests de send_appointment_reminders (Fase 4, tarea 4.2/4.3).

Todo mockeado: repos in-memory (fakes de appointment_fakes.py) para
citas/schedule, y mocks manuales para el repo de clientes y el sender de
WhatsApp. Sin llamadas reales a Supabase ni Meta.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.domain.appointment.entity import Appointment, AppointmentStatus, BusinessSchedule
from app.infrastructure.celery import reminders as reminders_module
from app.infrastructure.whatsapp.sender import WhatsAppSendResult, WhatsAppSendStatus
from tests.unit.appointment_fakes import FakeAppointmentRepository, FakeScheduleRepository

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
CLIENT_ID = str(uuid4())


def _make_appointment(
    *,
    client_id: str = CLIENT_ID,
    starts_at: datetime,
    status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    reminder_sent_at: datetime | None = None,
) -> Appointment:
    appt = Appointment(
        client_id=UUID(client_id),
        contact_phone="573000000000",
        contact_name="Ana",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        status=status,
    )
    appt.reminder_sent_at = reminder_sent_at
    return appt


def _fake_client_repo(
    *, has_credentials: bool = True, client_name: str = "Peluquería Ana"
) -> MagicMock:
    creds = SimpleNamespace(
        has_credentials=has_credentials,
        phone_number_id="tenant-pnid" if has_credentials else "",
        access_token="tenant-token" if has_credentials else "",
    )
    client = SimpleNamespace(name=client_name)
    repo = MagicMock()
    repo.get_whatsapp_credentials = AsyncMock(return_value=creds)
    repo.find_by_id = AsyncMock(return_value=client)
    return repo


def _settings(**overrides) -> SimpleNamespace:
    base = dict(
        reminder_beat_interval_minutes=10,
        whatsapp_phone_number_id="",
        whatsapp_access_token="",
        whatsapp_api_version="v22.0",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


async def _run(
    *,
    appointment_repo,
    schedule_repo,
    client_repo,
    settings,
    sender_result: WhatsAppSendResult | None = None,
):
    sender = MagicMock()
    sender.send.return_value = sender_result or WhatsAppSendResult(
        status=WhatsAppSendStatus.OK
    )

    with (
        patch.object(reminders_module, "get_settings", return_value=settings),
        patch.object(
            reminders_module, "_build_appointment_repo", return_value=appointment_repo
        ),
        patch.object(
            reminders_module, "_build_schedule_repo", return_value=schedule_repo
        ),
        patch.object(reminders_module, "_build_client_repo", return_value=client_repo),
        patch.object(reminders_module, "WhatsAppSender", return_value=sender),
    ):
        result = await reminders_module._send_appointment_reminders_async(now=NOW)
    return result, sender


# ======================================================================
# a) Selección de citas dentro de ventana correcta
# ======================================================================


class TestWindowSelection:
    @pytest.mark.asyncio
    async def test_appointment_inside_window_is_reminded(self) -> None:
        """offset=24h, beat=10min: cita en starts_at=NOW+24h cae en la
        ventana [NOW, NOW+10min) de remind_at → se envía."""
        appt = _make_appointment(starts_at=NOW + timedelta(hours=24))
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt)
        schedule_repo = FakeScheduleRepository(BusinessSchedule.default())
        client_repo = _fake_client_repo()
        settings = _settings()

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
        )

        assert result["sent"] == 1
        sender.send.assert_called_once()
        assert appt_repo.items[str(appt.id)].reminder_sent_at is not None

    @pytest.mark.asyncio
    async def test_appointment_before_window_is_not_reminded_yet(self) -> None:
        """remind_at cae ANTES de esta ventana (ej. el beat se retrasó o
        el offset del cliente es corto) — no se procesa en este ciclo.
        La cita SIGUE siendo candidata (starts_at futuro, dentro del
        rango amplio de 48h) pero su remind_at ya quedó atrás de
        [now, now+interval). Se simula con offset=10min y
        starts_at=NOW+2min → remind_at=NOW-8min < now."""
        appt = _make_appointment(starts_at=NOW + timedelta(minutes=2))
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt)
        schedule_repo = FakeScheduleRepository(
            BusinessSchedule(reminder_offset_minutes=10)
        )
        client_repo = _fake_client_repo()
        settings = _settings()

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
        )

        assert result["sent"] == 0
        assert result["skipped_out_of_window"] == 1
        sender.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_appointment_after_window_is_not_reminded_yet(self) -> None:
        """remind_at cae DESPUÉS de esta ventana — le toca a un ciclo
        futuro, no debe enviarse todavía."""
        appt = _make_appointment(starts_at=NOW + timedelta(hours=25))
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt)
        schedule_repo = FakeScheduleRepository(BusinessSchedule.default())  # offset 24h
        client_repo = _fake_client_repo()
        settings = _settings()

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
        )

        assert result["sent"] == 0
        assert result["skipped_out_of_window"] == 1
        sender.send.assert_not_called()
        assert appt_repo.items[str(appt.id)].reminder_sent_at is None


# ======================================================================
# b) Marcado idempotente
# ======================================================================


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_already_reminded_appointment_is_skipped(self) -> None:
        """Una cita con reminder_sent_at ya seteado NUNCA aparece entre los
        candidatos (find_reminder_candidates filtra reminder_sent_at IS
        NULL) — el fake replica esa semántica."""
        appt = _make_appointment(
            starts_at=NOW + timedelta(hours=24),
            reminder_sent_at=NOW - timedelta(hours=1),
        )
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt)
        schedule_repo = FakeScheduleRepository(BusinessSchedule.default())
        client_repo = _fake_client_repo()
        settings = _settings()

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
        )

        assert result["evaluated"] == 0
        assert result["sent"] == 0
        sender.send.assert_not_called()


# ======================================================================
# c) Salto de citas canceladas
# ======================================================================


class TestSkipsCancelled:
    @pytest.mark.asyncio
    async def test_cancelled_appointment_is_never_a_candidate(self) -> None:
        appt = _make_appointment(
            starts_at=NOW + timedelta(hours=24),
            status=AppointmentStatus.CANCELLED,
        )
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt)
        schedule_repo = FakeScheduleRepository(BusinessSchedule.default())
        client_repo = _fake_client_repo()
        settings = _settings()

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
        )

        assert result["evaluated"] == 0
        sender.send.assert_not_called()


# ======================================================================
# d) Continuación cuando un cliente no tiene credenciales
# ======================================================================


class TestResilience:
    @pytest.mark.asyncio
    async def test_continues_when_client_has_no_credentials(self) -> None:
        """Un cliente sin credenciales no debe lanzar excepción ni tumbar
        el resto de citas — se loguea warning y se sigue."""
        appt = _make_appointment(starts_at=NOW + timedelta(hours=24))
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt)
        schedule_repo = FakeScheduleRepository(BusinessSchedule.default())
        client_repo = _fake_client_repo(has_credentials=False)
        settings = _settings()  # sin fallback global tampoco

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
        )

        assert result["sent"] == 0
        assert result["skipped_no_credentials"] == 1
        sender.send.assert_not_called()
        # No se marca — se reintentará en el próximo ciclo
        assert appt_repo.items[str(appt.id)].reminder_sent_at is None

    @pytest.mark.asyncio
    async def test_one_client_failure_does_not_block_others(self) -> None:
        """Dos citas de dos clientes distintos: uno sin credenciales, el
        otro con credenciales válidas — el segundo debe enviarse igual."""
        client_ok = str(uuid4())
        client_bad = str(uuid4())
        appt_ok = _make_appointment(
            client_id=client_ok, starts_at=NOW + timedelta(hours=24)
        )
        appt_bad = _make_appointment(
            client_id=client_bad, starts_at=NOW + timedelta(hours=24)
        )
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt_ok)
        await appt_repo.save(appt_bad)

        schedule_repo = FakeScheduleRepository(BusinessSchedule.default())

        creds_ok = SimpleNamespace(
            has_credentials=True, phone_number_id="pnid-ok", access_token="token-ok"
        )
        creds_bad = SimpleNamespace(
            has_credentials=False, phone_number_id="", access_token=""
        )

        async def _get_creds(client_id: str):
            return creds_ok if client_id == client_ok else creds_bad

        client_repo = MagicMock()
        client_repo.get_whatsapp_credentials = AsyncMock(side_effect=_get_creds)
        client_repo.find_by_id = AsyncMock(
            return_value=SimpleNamespace(name="Negocio")
        )

        settings = _settings()

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
        )

        assert result["sent"] == 1
        assert result["skipped_no_credentials"] == 1
        sender.send.assert_called_once()
        assert appt_repo.items[str(appt_ok.id)].reminder_sent_at is not None
        assert appt_repo.items[str(appt_bad.id)].reminder_sent_at is None

    @pytest.mark.asyncio
    async def test_send_failure_does_not_mark_reminder_sent(self) -> None:
        appt = _make_appointment(starts_at=NOW + timedelta(hours=24))
        appt_repo = FakeAppointmentRepository()
        await appt_repo.save(appt)
        schedule_repo = FakeScheduleRepository(BusinessSchedule.default())
        client_repo = _fake_client_repo()
        settings = _settings()

        result, sender = await _run(
            appointment_repo=appt_repo,
            schedule_repo=schedule_repo,
            client_repo=client_repo,
            settings=settings,
            sender_result=WhatsAppSendResult(status=WhatsAppSendStatus.TOKEN_INVALID),
        )

        assert result["sent"] == 0
        assert result["failed"] == 1
        assert appt_repo.items[str(appt.id)].reminder_sent_at is None


# ======================================================================
# build_reminder_message — mensaje centralizado
# ======================================================================


class TestBuildReminderMessage:
    def test_includes_business_name_and_label(self) -> None:
        text = reminders_module.build_reminder_message(
            "Peluquería Ana", "lunes 7 de enero a las 10:00"
        )
        assert "Peluquería Ana" in text
        assert "lunes 7 de enero a las 10:00" in text

    def test_falls_back_to_generic_name_when_empty(self) -> None:
        text = reminders_module.build_reminder_message(
            "", "lunes 7 de enero a las 10:00"
        )
        assert "nuestro negocio" in text
