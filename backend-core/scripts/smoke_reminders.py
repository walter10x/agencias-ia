"""Smoke test stdlib-only de los recordatorios de cita (Fase 4).

Ejercita `send_appointment_reminders` con fakes/mocks manuales (sin
pytest, sin red, sin Supabase/Meta reales) para validar en un sandbox
sin dependencias instaladas:

  a) Selección de citas dentro de la ventana correcta (una cita dentro
     de la ventana, una antes, una después).
  b) Marcado idempotente: una cita con reminder_sent_at ya seteado se
     salta (nunca se reenvía).
  c) Salto de citas canceladas (nunca son candidatas).
  d) Continuación de la tarea cuando un cliente no tiene credenciales
     configuradas (no lanza excepción, sigue con las demás citas).

Uso:
    python3 scripts/smoke_reminders.py

NO sustituye a pytest — es un smoke check para sandboxes sin red/pip.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _install_dependency_stubs() -> None:
    """Stubs mínimos para libs externas no instaladas en el sandbox.

    Mismo criterio que scripts/smoke_appointments.py: solo se instala el
    stub si la librería real no está disponible, y solo lo mínimo para
    que los imports de app.infrastructure.celery.reminders y sus
    dependencias transitorias (celery, httpx, pydantic_settings, etc.)
    no exploten en un entorno sin `pip install` disponible.
    """

    def _try(name: str) -> bool:
        try:
            __import__(name)
            return True
        except ImportError:
            return False

    if not _try("pydantic_settings"):
        mod = types.ModuleType("pydantic_settings")

        class BaseSettings:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mod.BaseSettings = BaseSettings
        mod.SettingsConfigDict = dict
        sys.modules["pydantic_settings"] = mod

    if not _try("celery"):
        celery_mod = types.ModuleType("celery")

        class _FakeCelery:
            def __init__(self, *args, **kwargs) -> None:
                self.conf = SimpleNamespace(update=lambda **kw: None, beat_schedule={})

            def task(self, *dargs, **dkwargs):
                def decorator(fn):
                    fn.delay = lambda *a, **k: fn(*a, **k)
                    return fn

                if dargs and callable(dargs[0]) and not dkwargs:
                    return dargs[0]
                return decorator

        celery_mod.Celery = _FakeCelery
        sys.modules["celery"] = celery_mod

        celery_utils = types.ModuleType("celery.utils")
        celery_utils_log = types.ModuleType("celery.utils.log")

        import logging

        celery_utils_log.get_task_logger = lambda name: logging.getLogger(name)
        sys.modules["celery.utils"] = celery_utils
        sys.modules["celery.utils.log"] = celery_utils_log

    if not _try("httpx"):
        mod = types.ModuleType("httpx")

        class _HTTPError(Exception):
            pass

        class _TimeoutException(_HTTPError):
            pass

        class _ConnectError(_HTTPError):
            pass

        def _post(*args, **kwargs):
            raise RuntimeError("httpx stub: no debería llamarse en este smoke test")

        mod.HTTPError = _HTTPError
        mod.TimeoutException = _TimeoutException
        mod.ConnectError = _ConnectError
        mod.post = _post
        mod.request = _post
        sys.modules["httpx"] = mod


_install_dependency_stubs()

from app.domain.appointment.entity import (  # noqa: E402
    Appointment,
    AppointmentStatus,
    BusinessSchedule,
)
from app.infrastructure.celery import reminders as reminders_module  # noqa: E402
from app.infrastructure.whatsapp.sender import (  # noqa: E402
    WhatsAppSendResult,
    WhatsAppSendStatus,
)
from tests.unit.appointment_fakes import (  # noqa: E402
    FakeAppointmentRepository,
    FakeScheduleRepository,
)

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def _make_appointment(
    *,
    client_id: str,
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


def _fake_client_repo(*, has_credentials: bool = True) -> MagicMock:
    creds = SimpleNamespace(
        has_credentials=has_credentials,
        phone_number_id="tenant-pnid" if has_credentials else "",
        access_token="tenant-token" if has_credentials else "",
    )
    client = SimpleNamespace(name="Peluquería Ana")
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


async def _run_task(
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


# ---------------------------------------------------------------------------
# Casos de smoke
# ---------------------------------------------------------------------------


async def case_window_selection() -> None:
    """a) Una cita DENTRO de la ventana, una ANTES, una DESPUÉS."""
    client_id = str(uuid4())

    inside = _make_appointment(client_id=client_id, starts_at=NOW + timedelta(hours=24))
    # remind_at = starts_at - offset = (NOW+2min) - 10min = NOW-8min < now:
    # la cita YA es candidata (starts_at futuro, dentro del rango de 48h)
    # pero su instante de recordatorio quedó ANTES de esta ventana del beat.
    before = _make_appointment(client_id=client_id, starts_at=NOW + timedelta(minutes=2))
    after = _make_appointment(client_id=client_id, starts_at=NOW + timedelta(hours=25))

    # Caso "dentro": offset default (24h) sobre starts_at=NOW+24h => remind_at=NOW
    repo_inside = FakeAppointmentRepository()
    await repo_inside.save(inside)
    result, sender = await _run_task(
        appointment_repo=repo_inside,
        schedule_repo=FakeScheduleRepository(BusinessSchedule.default()),
        client_repo=_fake_client_repo(),
        settings=_settings(),
    )
    assert result["sent"] == 1, f"esperaba 1 enviado (dentro), obtuve {result}"
    assert repo_inside.items[str(inside.id)].reminder_sent_at is not None
    sender.send.assert_called_once()

    # Caso "antes": offset=10min sobre starts_at=NOW+2min => remind_at=NOW-8min < now
    repo_before = FakeAppointmentRepository()
    await repo_before.save(before)
    result, sender = await _run_task(
        appointment_repo=repo_before,
        schedule_repo=FakeScheduleRepository(BusinessSchedule(reminder_offset_minutes=10)),
        client_repo=_fake_client_repo(),
        settings=_settings(),
    )
    assert result["sent"] == 0, f"esperaba 0 enviados (antes), obtuve {result}"
    assert result["skipped_out_of_window"] == 1, f"obtuve {result}"
    sender.send.assert_not_called()

    # Caso "después": offset default (24h) sobre starts_at=NOW+25h => remind_at=NOW+1h
    repo_after = FakeAppointmentRepository()
    await repo_after.save(after)
    result, sender = await _run_task(
        appointment_repo=repo_after,
        schedule_repo=FakeScheduleRepository(BusinessSchedule.default()),
        client_repo=_fake_client_repo(),
        settings=_settings(),
    )
    assert result["sent"] == 0, f"esperaba 0 enviados (despues), obtuve {result}"
    assert result["skipped_out_of_window"] == 1
    sender.send.assert_not_called()
    assert repo_after.items[str(after.id)].reminder_sent_at is None


async def case_idempotent_mark() -> None:
    """b) Cita con reminder_sent_at ya seteado se salta (nunca reenvía)."""
    client_id = str(uuid4())
    appt = _make_appointment(
        client_id=client_id,
        starts_at=NOW + timedelta(hours=24),
        reminder_sent_at=NOW - timedelta(hours=1),
    )
    repo = FakeAppointmentRepository()
    await repo.save(appt)

    result, sender = await _run_task(
        appointment_repo=repo,
        schedule_repo=FakeScheduleRepository(BusinessSchedule.default()),
        client_repo=_fake_client_repo(),
        settings=_settings(),
    )

    assert result["evaluated"] == 0, f"no debería ser candidata, obtuve {result}"
    sender.send.assert_not_called()


async def case_skips_cancelled() -> None:
    """c) Cita cancelada nunca es candidata."""
    client_id = str(uuid4())
    appt = _make_appointment(
        client_id=client_id,
        starts_at=NOW + timedelta(hours=24),
        status=AppointmentStatus.CANCELLED,
    )
    repo = FakeAppointmentRepository()
    await repo.save(appt)

    result, sender = await _run_task(
        appointment_repo=repo,
        schedule_repo=FakeScheduleRepository(BusinessSchedule.default()),
        client_repo=_fake_client_repo(),
        settings=_settings(),
    )

    assert result["evaluated"] == 0, f"cancelada no debería ser candidata: {result}"
    sender.send.assert_not_called()


async def case_continues_without_credentials() -> None:
    """d) Cliente sin credenciales no lanza excepción y no bloquea a otros."""
    client_bad = str(uuid4())
    client_ok = str(uuid4())

    appt_bad = _make_appointment(client_id=client_bad, starts_at=NOW + timedelta(hours=24))
    appt_ok = _make_appointment(client_id=client_ok, starts_at=NOW + timedelta(hours=24))

    repo = FakeAppointmentRepository()
    await repo.save(appt_bad)
    await repo.save(appt_ok)

    creds_bad = SimpleNamespace(has_credentials=False, phone_number_id="", access_token="")
    creds_ok = SimpleNamespace(
        has_credentials=True, phone_number_id="pnid-ok", access_token="token-ok"
    )

    async def _get_creds(client_id: str):
        return creds_ok if client_id == client_ok else creds_bad

    client_repo = MagicMock()
    client_repo.get_whatsapp_credentials = AsyncMock(side_effect=_get_creds)
    client_repo.find_by_id = AsyncMock(return_value=SimpleNamespace(name="Negocio"))

    # No debe lanzar excepción aunque un cliente no tenga credenciales.
    result, sender = await _run_task(
        appointment_repo=repo,
        schedule_repo=FakeScheduleRepository(BusinessSchedule.default()),
        client_repo=client_repo,
        settings=_settings(),
    )

    assert result["sent"] == 1, f"el cliente OK debió recibir su recordatorio: {result}"
    assert result["skipped_no_credentials"] == 1
    sender.send.assert_called_once()
    assert repo.items[str(appt_ok.id)].reminder_sent_at is not None
    assert repo.items[str(appt_bad.id)].reminder_sent_at is None


async def case_send_failure_does_not_mark() -> None:
    """Extra: un envío fallido no marca reminder_sent_at (se reintenta)."""
    client_id = str(uuid4())
    appt = _make_appointment(client_id=client_id, starts_at=NOW + timedelta(hours=24))
    repo = FakeAppointmentRepository()
    await repo.save(appt)

    result, sender = await _run_task(
        appointment_repo=repo,
        schedule_repo=FakeScheduleRepository(BusinessSchedule.default()),
        client_repo=_fake_client_repo(),
        settings=_settings(),
        sender_result=WhatsAppSendResult(status=WhatsAppSendStatus.TOKEN_INVALID),
    )

    assert result["sent"] == 0
    assert result["failed"] == 1
    assert repo.items[str(appt.id)].reminder_sent_at is None


CASES = [
    ("window_selection (dentro/antes/despues)", case_window_selection),
    ("idempotent_mark (reminder_sent_at ya seteado)", case_idempotent_mark),
    ("skips_cancelled", case_skips_cancelled),
    ("continues_without_credentials", case_continues_without_credentials),
    ("send_failure_does_not_mark", case_send_failure_does_not_mark),
]


def main() -> int:
    passed = 0
    failed: list[tuple[str, str]] = []

    for name, coro_fn in CASES:
        try:
            asyncio.run(coro_fn())
            passed += 1
            print(f"PASS  {name}")
        except Exception:
            failed.append((name, traceback.format_exc()))
            print(f"FAIL  {name}")

    print(f"\n{passed} passed, {len(failed)} failed")
    for name, tb in failed:
        print(f"\nFAILED {name}\n{tb}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
