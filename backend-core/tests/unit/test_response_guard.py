"""Tests for anti-hallucination response guard."""

from __future__ import annotations

from app.infrastructure.ai.response_guard import enforce_tool_truth, tool_result_succeeded


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
    assert "agenda" in out.lower()


def test_blocks_soft_parking_without_tool() -> None:
    reply = (
        "Perfecto, Mathias. Hemos tomado nota de tu solicitud: sábado a las 11 am. "
        "Para confirmar la cita, nuestro equipo se pondrá en contacto contigo."
    )
    out = enforce_tool_truth(reply, [])
    assert "tomado nota" not in out.lower()
    assert "agenda" in out.lower()


def test_allows_booking_claim_after_successful_tool() -> None:
    reply = "Perfecto Mathias, quedas agendado mañana a las 11."
    out = enforce_tool_truth(reply, ["agendar_cita"])
    assert out == reply


def test_strips_email_promise() -> None:
    reply = (
        "Nos vemos mañana. Revisa tu correo (mrrxt1@gmail.com) "
        "para recibir el enlace de la reunión."
    )
    out = enforce_tool_truth(reply, ["agendar_cita"])
    assert "correo" not in out.lower()
    assert "email" not in out.lower()
