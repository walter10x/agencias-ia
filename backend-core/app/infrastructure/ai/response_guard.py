"""Guardas anti-alucinación: no confirmar hechos sin tool exitosa."""

from __future__ import annotations

import re

# Cualquier afirmación de que la cita ya quedó / se procesó / se anotó
_BOOKING_CLAIM = re.compile(
    r"("
    r"agendad\w*"
    r"|confirmad\w*"
    r"|reservad\w*"
    r"|qued(?:o|as?)\s+(?:agendad|apuntad|confirmad|listo|registrad)"
    r"|listo[,!]?\s+(?:mathias|ya|tu\s+cita|la\s+cita)?"
    r"|todo\s+bien"
    r"|ya\s+est[aá]\s+(?:hecha|list[ao]|agendada|confirmada|reservada)"
    r"|lo\s+(?:he\s+)?(?:agend|confirm|reserv|apunt|anot|hech)"
    r"|hemos?\s+(?:tomado\s+nota|registrado|anotado|apuntado|agendado|confirmado)"
    r"|nos\s+vemos\s+(?:mañana|el\s+\d|el\s+\w+)"
    r"|cita\s+(?:confirmada|agendada|reservada|lista)"
    r"|te\s+apunt[eéo]"
    r"|solicitud\s*(?::|de\s+cita)"
    r"|para\s+confirmar\s+la\s+cita"
    r"|equipo\s+se\s+pondr[aá]"
    r"|nos\s+pondremos?\s+en\s+contacto"
    r"|queda\s+(?:anotad|registrad|reservad|confirmad)"
    r"|apuntad[ao]\s+(?:para|el|mañana)"
    r")",
    re.IGNORECASE,
)
_EMAIL_CLAIM = re.compile(
    r"(e-?mail|correo\s+electr[oó]nico|\brevisa\s+tu\s+correo\b|te\s+enviaremos?\s+(?:un\s+)?(?:e-?mail|correo)"
    r"|invitaci[oó]n\s+con\s+e)",
    re.IGNORECASE,
)

_BOOKING_FALLBACK = (
    "Todavía no está confirmada en la agenda. "
    "Dime un día de lunes a viernes y una hora y la registro ahora mismo "
    "(solo te confirmo cuando quede guardada de verdad)."
)

_AGENDAR_OK = re.compile(r"cita agendada correctamente", re.IGNORECASE)
_AGENDAR_OK_CAPTURE = re.compile(
    r"Cita agendada correctamente para\s+(.+?)\s+el\s+(\S+).*?referencia:\s*([^\s).]+)",
    re.IGNORECASE | re.DOTALL,
)
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


def booking_confirmation_from_tool(content: str) -> str | None:
    """Mensaje fijo de confirmación a partir del resultado real de agendar_cita."""
    text = (content or "").strip()
    if not _AGENDAR_OK.search(text):
        return None
    m = _AGENDAR_OK_CAPTURE.search(text)
    if m:
        nombre, when, ref = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        who = nombre if nombre.lower() != "el cliente" else "ti"
        return (
            f"✅ Cita confirmada para {who} el {when}. "
            f"Referencia: {ref}. "
            "Queda guardada en nuestra agenda. Si necesitas cambiarla, dímelo."
        )
    return (
        "✅ Cita confirmada y guardada en la agenda. "
        "Si necesitas cambiarla, dímelo por este chat."
    )


def enforce_tool_truth(
    reply: str,
    successful_tools: list[str] | None,
    *,
    booking_tool_content: str | None = None,
) -> str:
    """Corrige confirmaciones inventadas si no hubo tool exitosa.

    Si ``agendar_cita`` sí tuvo éxito, sustituye la respuesta del LLM por un
    mensaje determinista basado en el resultado real de la tool (no confía
    en lo que el modelo invente).
    """
    ok = {t for t in (successful_tools or []) if t}
    booked = "agendar_cita" in ok

    if booked:
        fixed = booking_confirmation_from_tool(booking_tool_content or "")
        if fixed:
            return fixed
        return (
            "✅ Cita confirmada y guardada en la agenda. "
            "Si necesitas cambiarla, dímelo por este chat."
        )

    text = (reply or "").strip()
    if not text:
        return text

    if _BOOKING_CLAIM.search(text):
        return _BOOKING_FALLBACK

    if _EMAIL_CLAIM.search(text):
        cleaned = re.sub(
            r"[^.!?\n]*\b(?:e-?mail|correo)[^.!?\n]*[.!?]?",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        if not cleaned or _EMAIL_CLAIM.search(cleaned):
            return text if not _BOOKING_CLAIM.search(text) else _BOOKING_FALLBACK
        return cleaned

    return text
