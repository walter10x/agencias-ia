"""Tests del interceptor determinista sí → agendar_cita."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.infrastructure.ai.booking_confirm import (
    extract_pending_slot,
    is_user_affirmation,
    try_confirm_pending_booking,
)

_TZ = ZoneInfo("Europe/Madrid")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("sí", True),
        ("si", True),
        ("Sí!", True),
        ("ok", True),
        ("vale", True),
        ("dale", True),
        ("perfecto", True),
        ("confirmo", True),
        ("de acuerdo", True),
        ("[Mathias]: sí", True),
        ("lunes a las 10", False),
        ("sí pero mejor el martes", False),
        ("", False),
    ],
)
def test_is_user_affirmation(text: str, expected: bool) -> None:
    assert is_user_affirmation(text) is expected


def test_extract_slot_confirmamos_con_mes() -> None:
    history = [
        {
            "role": "assistant",
            "content": (
                "Puedo confirmarte ese hueco. "
                "¿Confirmamos el lunes 3 de agosto a las 10:00? Responde sí."
            ),
        }
    ]
    slot = extract_pending_slot(history)
    assert slot is not None
    assert slot.day == 3
    assert slot.month == 8
    assert slot.hour == 10
    assert slot.minute == 0


def test_extract_slot_weekday_day() -> None:
    history = [
        {
            "role": "assistant",
            "content": "¿Te viene bien el lunes 3 a las 10:00?",
        }
    ]
    slot = extract_pending_slot(history)
    assert slot is not None
    assert slot.day == 3
    assert slot.hour == 10


def test_extract_slot_iso() -> None:
    history = [
        {"role": "assistant", "content": "Hueco libre: 2026-08-03T10:00"},
    ]
    slot = extract_pending_slot(history)
    assert slot == datetime(2026, 8, 3, 10, 0, tzinfo=_TZ)


@pytest.mark.asyncio
async def test_try_confirm_calls_agendar_cita() -> None:
    history = [
        {
            "role": "assistant",
            "content": "¿Confirmamos el lunes 3 de agosto a las 10:00? Responde sí.",
        }
    ]
    ctx = {
        "id": "a1111111-1111-1111-1111-111111111111",
        "phone": "+34688878205",
        "contact_phone": "+34688878205",
        "contact_name": "Mathias",
    }
    ok = (
        "Cita agendada correctamente para Mathias "
        "el 2026-08-03T10:00:00+02:00 (referencia: abc-123). "
        "Confirma al cliente la fecha y hora."
    )
    with patch(
        "app.infrastructure.ai.booking_confirm.execute_tool",
        new_callable=AsyncMock,
        return_value=ok,
    ) as mock_tool:
        reply = await try_confirm_pending_booking("sí", history, ctx)

    assert reply is not None
    assert "✅" in reply
    assert "confirmada" in reply.lower()
    mock_tool.assert_awaited_once()
    args = mock_tool.await_args
    assert args.args[0] == "agendar_cita"
    assert "2026-08-03T10:00" in args.args[1]["fecha_hora"]


@pytest.mark.asyncio
async def test_try_confirm_skips_without_affirmation() -> None:
    history = [
        {"role": "assistant", "content": "¿Confirmamos el lunes 3 de agosto a las 10:00?"},
    ]
    reply = await try_confirm_pending_booking(
        "mejor el martes",
        history,
        {"id": "x", "phone": "+34600000000"},
    )
    assert reply is None


@pytest.mark.asyncio
async def test_try_confirm_skips_without_slot() -> None:
    reply = await try_confirm_pending_booking(
        "sí",
        [{"role": "assistant", "content": "Hola, ¿en qué te ayudo?"}],
        {"id": "x", "phone": "+34600000000"},
    )
    assert reply is None
