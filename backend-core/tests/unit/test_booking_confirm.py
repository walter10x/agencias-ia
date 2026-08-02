"""Tests del interceptor determinista sí → agendar_cita."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.infrastructure.ai.booking_confirm import (
    extract_pending_slot,
    extract_slot_from_text,
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
        ("Si, confirmo", True),
        ("[Mathias]: sí", True),
        ("lunes a las 10", False),
        ("sí pero mejor el martes", False),
        ("", False),
    ],
)
def test_is_user_affirmation(text: str, expected: bool) -> None:
    assert is_user_affirmation(text) is expected


@pytest.mark.parametrize(
    "text",
    [
        "¿Confirmamos el lunes a las 10:00? Responde sí.",
        "¿Confirmamos lunes a las 10?",
        "Perfecto, el lunes a las 10 te va bien. Responde sí para confirmar.",
        "¿Te viene bien el lunes 3 a las 10:00?",
        "¿Confirmamos el lunes 3 de agosto a las 10:00?",
        "quiero demo el lunes a las 11",
        "lunes a las 10",
    ],
)
def test_extract_common_spanish_slots(text: str) -> None:
    slot = extract_slot_from_text(text)
    assert slot is not None
    assert slot.tzinfo is not None
    assert 7 <= slot.hour <= 21


def test_extract_ignores_guard_fallback() -> None:
    text = (
        "Todavía no está confirmada en la agenda. "
        "Dime un día de lunes a viernes y una hora…"
    )
    assert extract_slot_from_text(text) is None


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


def test_extract_slot_from_user_history() -> None:
    history = [
        {"role": "user", "content": "quiero el lunes a las 10"},
        {
            "role": "assistant",
            "content": "Todavía no está confirmada en la agenda. Dime un día…",
        },
    ]
    slot = extract_pending_slot(history)
    assert slot is not None
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
            "content": "¿Confirmamos el lunes a las 10:00? Responde sí.",
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
        "el 2026-08-04T10:00:00+02:00 (referencia: abc-123). "
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
    mock_tool.assert_awaited_once()
    assert mock_tool.await_args.args[0] == "agendar_cita"


@pytest.mark.asyncio
async def test_try_book_from_user_day_time() -> None:
    ctx = {"id": "x", "phone": "+34600000000", "contact_phone": "+34600000000"}
    ok = (
        "Cita agendada correctamente para el cliente "
        "el 2026-08-04T10:00:00+02:00 (referencia: xyz). "
        "Confirma al cliente la fecha y hora."
    )
    with patch(
        "app.infrastructure.ai.booking_confirm.execute_tool",
        new_callable=AsyncMock,
        return_value=ok,
    ) as mock_tool:
        reply = await try_confirm_pending_booking(
            "quiero el lunes a las 10",
            [],
            ctx,
        )
    assert reply is not None
    assert "✅" in reply
    mock_tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_try_book_time_only_with_history_day() -> None:
    """Caso real Mathias: 'lunes en la mañana' → bot pide hora → '10 am'."""
    history = [
        {
            "role": "user",
            "content": "Quiero agendar una cita para el lunes en la mañana",
        },
        {
            "role": "assistant",
            "content": (
                "¡Hola Mathias! El lunes sería el 3 de agosto. "
                "¿Qué hora exacta de la mañana te conviene? Así la agendo de una vez."
            ),
        },
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
        reply = await try_confirm_pending_booking("10 am", history, ctx)

    assert reply is not None
    assert "✅" in reply
    mock_tool.assert_awaited_once()
    assert "2026-08-03T10:00" in mock_tool.await_args.args[1]["fecha_hora"]


@pytest.mark.parametrize(
    "text,hour",
    [
        ("10 am", 10),
        ("10am", 10),
        ("10:00", 10),
        ("a las 10", 10),
        ("11:30 am", 11),
        ("3 pm", 15),
    ],
)
def test_extract_time_only(text: str, hour: int) -> None:
    from app.infrastructure.ai.booking_confirm import extract_time_only

    got = extract_time_only(text)
    assert got is not None
    assert got[0] == hour


@pytest.mark.asyncio
async def test_try_confirm_skips_without_affirmation() -> None:
    history = [
        {"role": "assistant", "content": "¿Confirmamos el lunes 3 de agosto a las 10:00?"},
    ]
    reply = await try_confirm_pending_booking(
        "mejor el martes por la tarde",
        history,
        {"id": "x", "phone": "+34600000000"},
    )
    assert reply is None


@pytest.mark.asyncio
async def test_affirmation_without_slot_asks_day_hour() -> None:
    reply = await try_confirm_pending_booking(
        "sí",
        [{"role": "assistant", "content": "Hola, ¿en qué te ayudo?"}],
        {"id": "x", "phone": "+34600000000"},
    )
    assert reply is not None
    assert "lunes a las 10" in reply.lower()
