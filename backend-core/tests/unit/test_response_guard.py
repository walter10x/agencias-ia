"""Tests for anti-hallucination response guard."""

from __future__ import annotations

from app.infrastructure.ai.response_guard import (
    booking_confirmation_from_tool,
    enforce_tool_truth,
    tool_result_succeeded,
)


def test_tool_result_agendar_ok() -> None:
    assert tool_result_succeeded(
        "agendar_cita",
        "Cita agendada correctamente para Mathias el 2026-07-31T11:00 (referencia: abc).",
    )


def test_tool_result_agendar_fail() -> None:
    assert not tool_result_succeeded(
        "agendar_cita",
        "No se pudo completar la operación: slot ocupado",
    )


def test_blocks_fake_booking_without_tool() -> None:
    reply = "¡Listo! Quedas agendado mañana a las 11 am por videollamada."
    out = enforce_tool_truth(reply, [])
    assert "agendado mañana" not in out.lower()
    assert "todavía no" in out.lower() or "agenda" in out.lower()


def test_blocks_soft_parking_without_tool() -> None:
    reply = (
        "Perfecto, Mathias. Hemos tomado nota de tu solicitud: sábado a las 11 am. "
        "Para confirmar la cita, nuestro equipo se pondrá en contacto contigo."
    )
    out = enforce_tool_truth(reply, [])
    assert "tomado nota" not in out.lower()
    assert "todavía no" in out.lower() or "agenda" in out.lower()


def test_allows_confirmamos_question_without_tool() -> None:
    """Regression: asking ¿Confirmamos…? must NOT be replaced by the fallback loop."""
    reply = "¿Confirmamos el lunes 4 de agosto a las 11:00? Responde sí."
    out = enforce_tool_truth(reply, [])
    assert out == reply
    assert "todavía no" not in out.lower()


def test_allows_availability_offer_with_question() -> None:
    reply = (
        "Para el lunes 4 de agosto tengo 11:00 y 12:00. "
        "¿Te va bien a las 11:00?"
    )
    out = enforce_tool_truth(reply, [])
    assert out == reply


def test_blocks_todo_bien_claim_without_tool() -> None:
    reply = "Todo bien Mathias, lo he agendado para el lunes a las 11."
    out = enforce_tool_truth(reply, [])
    assert "lo he agendado" not in out.lower()
    assert "todavía no" in out.lower() or "agenda" in out.lower()


def test_deterministic_confirmation_when_tool_ok() -> None:
    tool_content = (
        "Cita agendada correctamente para Mathias el 2026-08-04T11:00:00+02:00 "
        "(referencia: abc-123). Confirma al cliente la fecha y hora."
    )
    out = enforce_tool_truth(
        "Bla bla inventado",
        ["agendar_cita"],
        booking_tool_content=tool_content,
    )
    assert out.startswith("✅")
    assert "abc-123" in out
    assert "Mathias" in out
    assert "bla bla" not in out.lower()


def test_booking_confirmation_parser() -> None:
    msg = booking_confirmation_from_tool(
        "Cita agendada correctamente para Mathias el 2026-08-04T11:00 (referencia: xyz)."
    )
    assert msg is not None
    assert "Mathias" in msg
    assert "xyz" in msg


def test_strips_email_promise() -> None:
    reply = (
        "Nos vemos mañana. Revisa tu correo (mrrxt1@gmail.com) "
        "para recibir el enlace de la reunión."
    )
    out = enforce_tool_truth(
        reply,
        ["agendar_cita"],
        booking_tool_content=(
            "Cita agendada correctamente para Mathias el 2026-08-01T11:00 "
            "(referencia: r1)."
        ),
    )
    assert "correo" not in out.lower()
    assert "email" not in out.lower()
    assert out.startswith("✅")
