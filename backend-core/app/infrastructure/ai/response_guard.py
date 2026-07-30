"""Guardas anti-alucinación: no confirmar hechos sin tool exitosa."""

from __future__ import annotations

import re

_BOOKING_CLAIM = re.compile(
    r"(agendad\w*|confirmad\w*\s+la\s+cita|qued(?:o|as?)\s+(?:agendad|apuntad|confirmad)"
    r"|nos\s+vemos\s+(?:mañana|el\s+\d)|cita\s+(?:confirmada|agendada|para\s+mañana)"
    r"|te\s+apunt[eéo]|queda\s+reservad)",
    re.IGNORECASE,
)
_EMAIL_CLAIM = re.compile(
    r"(e-?mail|correo\s+electr[oó]nico|\brevisa\s+tu\s+correo\b|te\s+enviaremos?\s+(?:un\s+)?(?:e-?mail|correo)"
    r"|invitaci[oó]n\s+con\s+e)",
    re.IGNORECASE,
)

_BOOKING_FALLBACK = (
    "Para dejar la cita confirmada necesito registrarla en la agenda. "
    "Dime otra vez el día y la hora que te vienen bien y la apunto ahora mismo."
)

_AGENDAR_OK = re.compile(r"cita agendada correctamente", re.IGNORECASE)
_TOOL_FAIL = re.compile(
    r"^(error|no se pudo|falta el|tool ')",
    re.IGNORECASE,
)


def tool_result_succeeded(tool_name: str, content: str) -> bool:
    """True si el string de resultado indica éxito usable por el LLM."""
    text = (content or "").strip()
    if not text or _TOOL_FAIL.search(text):
        return False
    if tool_name == "agendar_cita":
        return bool(_AGENDAR_OK.search(text))
    return True


def enforce_tool_truth(reply: str, successful_tools: list[str] | None) -> str:
    """Corrige confirmaciones inventadas si no hubo tool exitosa.

    - No confirmar cita sin ``agendar_cita`` OK.
    - No prometer email / correo (aún no hay tool de email).
    """
    text = (reply or "").strip()
    if not text:
        return text

    ok = {t for t in (successful_tools or []) if t}
    booked = "agendar_cita" in ok

    if _BOOKING_CLAIM.search(text) and not booked:
        return _BOOKING_FALLBACK

    if _EMAIL_CLAIM.search(text):
        # Quitar frases que prometen email; si queda vacío, mensaje neutro.
        cleaned = re.sub(
            r"[^.!?\n]*\b(?:e-?mail|correo)[^.!?\n]*[.!?]?",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        if not cleaned:
            if booked:
                return (
                    "Cita confirmada. El equipo de Orinoco te contactará "
                    "por este mismo chat si hace falta."
                )
            return text  # sin booking claim ya pasó; dejar texto sin email si falla clean
        text = cleaned
        # Por si quedó muñón raro
        if _EMAIL_CLAIM.search(text):
            text = (
                "Perfecto. El equipo de Orinoco te contactará por WhatsApp "
                "si necesitáis más detalles."
            )

    return text
