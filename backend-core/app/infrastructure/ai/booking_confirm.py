"""Confirmación determinista de citas (sí → agendar_cita).

Los bots profesionales NO delegan el paso crítico «sí» solo al LLM:
si el asistente ya propuso un hueco («¿Confirmamos el lunes…?») y el
cliente afirma, se llama a ``agendar_cita`` sin depender del modelo.
"""

from __future__ import annotations

import logging
import re
from calendar import monthrange
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from app.infrastructure.ai.response_guard import (
    booking_confirmation_from_tool,
    tool_result_succeeded,
)
from app.infrastructure.ai.tools import execute_tool

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Europe/Madrid")

_MONTHS: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# Afirmaciones cortas típicas de WhatsApp tras «¿Confirmamos…?»
_AFFIRM = re.compile(
    r"^\s*(?:sí|si|ok|okay|vale|dale|perfecto|confirmo|confirmame|confírmame|"
    r"de\s+acuerdo|claro|vamos|adelante|hecho|sí\s+por\s+favor|si\s+por\s+favor|"
    r"sí\s+confirma|si\s+confirma|me\s+va\s+bien|te\s+confirmo)"
    r"(?:\s*[!.]*)?\s*$",
    re.IGNORECASE,
)

# Hueco propuesto en el último mensaje del bot
_SLOT_WITH_MONTH = re.compile(
    r"(?:confirmamos|te\s+viene\s+bien|te\s+va\s+bien|confirmarte|quedamos|"
    r"apunto|apuntar|reservar|hueco)"
    r".{0,100}?"
    r"(?:el\s+)?"
    r"(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)?\s*"
    r"(?:d[ií]a\s+)?"
    r"(\d{1,2})\s+de\s+"
    r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre)"
    r".{0,40}?"
    r"(?:a\s+las?\s+|a\s+la\s+)(\d{1,2})(?::(\d{2}))?",
    re.IGNORECASE | re.DOTALL,
)

_SLOT_WEEKDAY_DAY = re.compile(
    r"(?:confirmamos|te\s+viene\s+bien|te\s+va\s+bien|confirmarte|quedamos)"
    r".{0,80}?"
    r"(?:el\s+)?(?:lunes|martes|mi[eé]rcoles|jueves|viernes)\s+"
    r"(\d{1,2})"
    r"(?:\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
    r"setiembre|octubre|noviembre|diciembre))?"
    r".{0,30}?"
    r"(?:a\s+las?\s+|a\s+la\s+)(\d{1,2})(?::(\d{2}))?",
    re.IGNORECASE | re.DOTALL,
)

_ISO_SLOT = re.compile(
    r"(20\d{2})-(\d{2})-(\d{2})[T\s](\d{1,2}):(\d{2})",
)


def is_user_affirmation(text: str) -> bool:
    """True si el mensaje es un sí/ok corto de confirmación."""
    raw = (text or "").strip()
    # Quitar prefijo "[Nombre]: " si viene envuelto
    if raw.startswith("[") and "]: " in raw[:80]:
        raw = raw.split("]: ", 1)[-1].strip()
    if not raw or len(raw) > 80:
        return False
    return bool(_AFFIRM.match(raw))


def _resolve_date(day: int, month: int | None, hour: int, minute: int) -> datetime | None:
    """Construye datetime en Europe/Madrid; si el día ya pasó, mes/año siguiente."""
    now = datetime.now(_TZ)
    if month is None:
        month = now.month
        # Si el día del mes ya pasó este mes, probar mes siguiente
        try:
            candidate = date(now.year, month, day)
        except ValueError:
            return None
        if candidate < now.date():
            if month == 12:
                month = 1
                year = now.year + 1
            else:
                month += 1
                year = now.year
        else:
            year = now.year
    else:
        year = now.year
        try:
            candidate = date(year, month, day)
        except ValueError:
            # día inválido (31 feb, etc.)
            last = monthrange(year, month)[1]
            if day > last:
                return None
            candidate = date(year, month, day)
        if candidate < now.date():
            year += 1
            try:
                candidate = date(year, month, day)
            except ValueError:
                return None

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return datetime.combine(candidate, time(hour, minute), tzinfo=_TZ)


def extract_pending_slot(history: list[dict[str, Any]]) -> datetime | None:
    """Busca en mensajes recientes del asistente un hueco propuesto."""
    for msg in reversed(history or []):
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = str(msg.get("content") or "")
        if not content.strip():
            continue

        m = _ISO_SLOT.search(content)
        if m:
            try:
                return datetime(
                    int(m.group(1)),
                    int(m.group(2)),
                    int(m.group(3)),
                    int(m.group(4)),
                    int(m.group(5)),
                    tzinfo=_TZ,
                )
            except ValueError:
                pass

        m = _SLOT_WITH_MONTH.search(content)
        if m:
            day = int(m.group(1))
            month = _MONTHS.get(m.group(2).lower())
            hour = int(m.group(3))
            minute = int(m.group(4) or "0")
            dt = _resolve_date(day, month, hour, minute)
            if dt:
                return dt

        m = _SLOT_WEEKDAY_DAY.search(content)
        if m:
            day = int(m.group(1))
            month_name = m.group(2)
            month = _MONTHS.get(month_name.lower()) if month_name else None
            hour = int(m.group(3))
            minute = int(m.group(4) or "0")
            dt = _resolve_date(day, month, hour, minute)
            if dt:
                return dt

    return None


def _format_success(dt: datetime) -> str:
    dias = (
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo",
    )
    meses = (
        "",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )
    local = dt.astimezone(_TZ)
    return (
        f"✅ Cita confirmada: {dias[local.weekday()]} "
        f"{local.day} de {meses[local.month]} a las "
        f"{local.strftime('%H:%M')}. ¿Necesitas algo más?"
    )


async def try_confirm_pending_booking(
    user_text: str,
    history: list[dict[str, Any]],
    client_context: dict[str, Any],
) -> str | None:
    """Si el usuario dice sí y hay hueco pendiente, agenda y devuelve el texto.

    Returns:
        Respuesta lista para WhatsApp, o None si no aplica (seguir con el LLM).
    """
    if not is_user_affirmation(user_text):
        return None

    slot = extract_pending_slot(history)
    if slot is None:
        logger.info("booking_confirm: affirmation without parseable slot in history")
        return None

    fecha_hora = slot.strftime("%Y-%m-%dT%H:%M")
    logger.info("booking_confirm: affirmative → agendar_cita %s", fecha_hora)

    try:
        result = await execute_tool(
            "agendar_cita",
            {
                "fecha_hora": fecha_hora,
                "servicio": "Cita",
                "notas": "Confirmación por WhatsApp",
            },
            client_context,
        )
    except Exception:
        logger.exception("booking_confirm: agendar_cita raised")
        return (
            "No pude guardar la cita ahora mismo. "
            "Dime de nuevo el día y la hora (lunes a viernes) y lo intento."
        )

    content = str(result or "")
    if not tool_result_succeeded("agendar_cita", content):
        logger.warning("booking_confirm: tool failed: %s", content[:200])
        if len(content.strip()) > 10 and not content.strip().startswith("{"):
            return content.strip()
        return (
            "Ese hueco ya no está libre. "
            "Dime otro día de lunes a viernes y te busco disponibilidad."
        )

    return booking_confirmation_from_tool(content) or _format_success(slot)
