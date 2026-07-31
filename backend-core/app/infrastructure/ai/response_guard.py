"""Guardas anti-alucinación: no confirmar hechos sin tool exitosa."""

from __future__ import annotations

import re

# Afirmaciones de que la cita YA quedó hecha (no preguntas "¿confirmamos?").
_BOOKING_CLAIM = re.compile(
    r"("
    r"(?<![¿?])\bagendad[ao]s?\b"
    r"|(?<![¿?])\bconfirmad[ao]s?\b"
    r"|(?<![¿?])\breservad[ao]s?\b"
    r"|\bqued(?:o|as)\s+(?:agendad|apuntad|confirmad|listo|registrad)"
    r"|\bya\s+(?:est[aá]\s+)?(?:agendad|confirmad|reservad|apuntad|list[ao])"
    r"|\btodo\s+bien\b.{0,40}\b(?:agend|confirm|reserv)"
    r"|\blo\s+(?:he\s+)?(?:agendado|confirmado|reservado|apuntado|anotado)"
    r"|\bhemos?\s+(?:tomado\s+nota|registrado|anotado|apuntado|agendado|confirmado)\b"
    r"|\bnos\s+vemos\s+(?:mañana|el\s+\d)"
    r"|\bcita\s+(?:confirmada|agendada|reservada)\b"
    r"|\bte\s+apunt[eéo]\b"
    r"|\bequipo\s+se\s+pondr[aá]\b"
    r"|\bel\s+equipo\s+te\s+contactar[aá]\b"
    r"|\bte\s+contactar[aá]\b.{0,40}\bconfirm"
    r"|\bnos\s+pondremos?\s+en\s+contacto\b"
    r"|\bqueda\s+(?:anotad|registrad|reservad|confirmad|agendad)"
    r"|\bcomo\s+tu\s+preferencia\b"
    r"|\btu\s+preferencia\b"
    r"|\bpara\s+confirmar\s+la\s+cita\b"
    r"|\btomamos?\s+nota\b"
    r")",
    re.IGNORECASE | re.DOTALL,
)

# Preguntas de confirmación al cliente — NO son claims falsos
_BOOKING_QUESTION = re.compile(
    r"(¿\s*)?(confirmamos|te\s+confirmo|confirmas|te\s+parece|de\s+acuerdo|"
    r"te\s+va\s+bien|okey\??|ok\??)\b",
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


def looks_like_booking_question(text: str) -> bool:
    """True si el mensaje pide confirmación de hueco al cliente.

    No basta con cualquier '?': un soft-park + '¿Hay algo más?' no es
    pregunta de confirmación de cita.
    """
    t = (text or "").strip()
    if not t:
        return False
    return bool(_BOOKING_QUESTION.search(t))


def enforce_tool_truth(
    reply: str,
    successful_tools: list[str] | None,
    *,
    booking_tool_content: str | None = None,
) -> str:
    """Corrige confirmaciones inventadas si no hubo tool exitosa.

    Si ``agendar_cita`` sí tuvo éxito, sustituye la respuesta del LLM por un
    mensaje determinista basado en el resultado real de la tool.
    Las preguntas del tipo «¿Confirmamos el lunes…?» se dejan pasar.
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

    # Soft-park / "ya está" inventado: siempre bloquea, aunque lleve
    # un "¿algo más?" al final.
    if _BOOKING_CLAIM.search(text):
        return _BOOKING_FALLBACK

    # Pregunta legítima de confirmación de hueco (¿Confirmamos…?).
    if looks_like_booking_question(text):
        if _EMAIL_CLAIM.search(text):
            cleaned = re.sub(
                r"[^.!?\n]*\b(?:e-?mail|correo)[^.!?\n]*[.!?]?",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()
            return cleaned or text
        return text

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
