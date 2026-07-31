"""Confirmación determinista de citas (sí / día+hora → agendar_cita).

No depende del LLM para el paso crítico: parsea huecos en español
(«lunes a las 10», «¿Confirmamos el lunes…?») y llama a ``agendar_cita``.
"""

from __future__ import annotations

import logging
import re
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.infrastructure.ai.response_guard import (
    booking_confirmation_from_tool,
    tool_result_succeeded,
)
from app.infrastructure.ai.tools import execute_tool

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Europe/Madrid")

_WEEKDAYS: dict[str, int] = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}

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

_WEEKDAY_ALT = (
    r"lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo"
)
_MONTH_ALT = (
    r"enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre"
)

_AFFIRM = re.compile(
    r"^\s*(?:sí|si|ok|okay|vale|dale|perfecto|confirmo|confirmame|confírmame|"
    r"de\s+acuerdo|claro|vamos|adelante|hecho|"
    r"sí\s*,?\s*(?:por\s+favor|confirma(?:me)?|confirmo)?|"
    r"si\s*,?\s*(?:por\s+favor|confirma(?:me)?|confirmo)?|"
    r"ok\s*,?\s*confirma(?:me)?|"
    r"me\s+va\s+bien|te\s+confirmo|eso\s+mismo|ese\s+hueco)"
    r"(?:\s*[!.]*)?\s*$",
    re.IGNORECASE,
)

_BOOKING_INTENT = re.compile(
    r"\b(?:cita|agend|demo|reserv|quiero|necesito|puedo|apunta(?:me)?|"
    r"confirma(?:me)?|para\s+el|me\s+viene|me\s+va)\b",
    re.IGNORECASE,
)

_ISO_SLOT = re.compile(
    r"(20\d{2})-(\d{2})-(\d{2})[T\s](\d{1,2}):(\d{2})",
)

_SLOT_DAY_MONTH = re.compile(
    rf"(?:(?:{_WEEKDAY_ALT})\s+)?"
    rf"(\d{{1,2}})\s+de\s+({_MONTH_ALT})"
    rf".{{0,40}}?"
    r"(?:a\s+las?\s+|a\s+la\s+|a\s+|las?\s+)?"
    r"(\d{1,2})(?::(\d{2}))?\s*(?:h(?:oras?)?|am|pm)?",
    re.IGNORECASE | re.DOTALL,
)

_SLOT_WEEKDAY_DOM = re.compile(
    rf"(?:el\s+)?({_WEEKDAY_ALT})\s+(\d{{1,2}})"
    rf"(?:\s+de\s+({_MONTH_ALT}))?"
    rf".{{0,30}}?"
    r"(?:a\s+las?\s+|a\s+la\s+|a\s+|las?\s+)"
    r"(\d{1,2})(?::(\d{2}))?\s*(?:h(?:oras?)?|am|pm)?",
    re.IGNORECASE | re.DOTALL,
)

# «el lunes a las 10:00» / «¿Confirmamos el lunes a las 10?»
_SLOT_WEEKDAY_TIME = re.compile(
    rf"(?:el\s+)?({_WEEKDAY_ALT})"
    rf"(?:\s+(?:por\s+la\s+)?(?:mañana|tarde))?"
    rf".{{0,40}}?"
    r"(?:a\s+las?\s+|a\s+la\s+|las?\s+)"
    r"(\d{1,2})(?::(\d{2}))?\s*(?:h(?:oras?)?|am|pm)?",
    re.IGNORECASE | re.DOTALL,
)

# «lunes 10» / «lunes 10am» (hora laboral)
_SLOT_WEEKDAY_HOUR = re.compile(
    rf"(?:el\s+)?({_WEEKDAY_ALT})\s+(\d{{1,2}})(?::(\d{{2}}))?\s*(am|pm|h)?\b",
    re.IGNORECASE,
)

_FALLBACK_GUARD = re.compile(r"todav[ií]a\s+no\s+est[aá]\s+confirmada", re.I)


def _strip_user_wrapper(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("[") and "]: " in raw[:80]:
        raw = raw.split("]: ", 1)[-1].strip()
    return raw


def _weekday_index(name: str) -> int | None:
    key = (name or "").lower().strip()
    if key in _WEEKDAYS:
        return _WEEKDAYS[key]
    folded = key.replace("é", "e").replace("á", "a")
    return _WEEKDAYS.get(folded)


def is_user_affirmation(text: str) -> bool:
    """True si el mensaje es un sí/ok corto de confirmación."""
    raw = _strip_user_wrapper(text)
    if not raw or len(raw) > 90:
        return False
    return bool(_AFFIRM.match(raw))


def looks_like_booking_request(text: str) -> bool:
    """True si el mensaje pide cita y trae día/hora."""
    raw = _strip_user_wrapper(text)
    if not raw or extract_slot_from_text(raw) is None:
        return False
    if _BOOKING_INTENT.search(raw):
        return True
    # Mensaje corto solo con día+hora: «lunes a las 10»
    return len(raw) <= 50


def _normalize_hour(hour: int, ampm: str | None = None) -> int | None:
    if hour < 0 or hour > 23:
        return None
    token = (ampm or "").lower()
    if token == "pm" and 1 <= hour <= 11:
        return hour + 12
    if token == "am" and hour == 12:
        return 0
    return hour


def _next_weekday(weekday: int, hour: int, minute: int) -> datetime:
    """Próximo día de la semana (hoy si aún no pasó la hora)."""
    now = datetime.now(_TZ)
    today = now.date()
    days_ahead = (weekday - today.weekday()) % 7
    candidate = today + timedelta(days=days_ahead)
    dt = datetime.combine(candidate, time(hour, minute), tzinfo=_TZ)
    if dt <= now:
        dt = dt + timedelta(days=7)
    return dt


def _resolve_date(day: int, month: int | None, hour: int, minute: int) -> datetime | None:
    """Construye datetime en Europe/Madrid; si el día ya pasó, mes/año siguiente."""
    now = datetime.now(_TZ)
    if month is None:
        month = now.month
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
            try:
                candidate = date(year, month, day)
            except ValueError:
                return None
        else:
            year = now.year
    else:
        year = now.year
        try:
            candidate = date(year, month, day)
        except ValueError:
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


def _ampm_in(fragment: str) -> str | None:
    low = fragment.lower()
    if re.search(r"\bpm\b", low):
        return "pm"
    if re.search(r"\bam\b", low):
        return "am"
    return None


def extract_slot_from_text(content: str) -> datetime | None:
    """Extrae un hueco datetime de un texto libre en español."""
    text = content or ""
    if not text.strip() or _FALLBACK_GUARD.search(text):
        return None

    m = _ISO_SLOT.search(text)
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

    m = _SLOT_DAY_MONTH.search(text)
    if m:
        day = int(m.group(1))
        month = _MONTHS.get(m.group(2).lower())
        hour = int(m.group(3))
        minute = int(m.group(4) or "0")
        hour_n = _normalize_hour(hour, _ampm_in(text[m.start() : m.end()]))
        if hour_n is not None:
            dt = _resolve_date(day, month, hour_n, minute)
            if dt:
                return dt

    m = _SLOT_WEEKDAY_DOM.search(text)
    if m:
        wd = _weekday_index(m.group(1))
        day = int(m.group(2))
        month_name = m.group(3)
        month = _MONTHS.get(month_name.lower()) if month_name else None
        hour = int(m.group(4))
        minute = int(m.group(5) or "0")
        hour_n = _normalize_hour(hour, _ampm_in(text[m.start() : m.end()]))
        if wd is not None and hour_n is not None:
            dt = _resolve_date(day, month, hour_n, minute)
            if dt:
                return dt

    m = _SLOT_WEEKDAY_TIME.search(text)
    if m:
        wd = _weekday_index(m.group(1))
        hour = int(m.group(2))
        minute = int(m.group(3) or "0")
        hour_n = _normalize_hour(hour, _ampm_in(text[m.start() : m.end()]))
        if wd is not None and hour_n is not None:
            return _next_weekday(wd, hour_n, minute)

    m = _SLOT_WEEKDAY_HOUR.search(text)
    if m:
        wd = _weekday_index(m.group(1))
        hour = int(m.group(2))
        minute = int(m.group(3) or "0")
        ampm = (m.group(4) or "").lower()
        if ampm not in ("am", "pm"):
            ampm = ""
        hour_n = _normalize_hour(hour, ampm or None)
        # Solo horas laborales para no confundir «lunes 3» (día 3) sin "a las"
        if wd is not None and hour_n is not None and 7 <= hour_n <= 21:
            # Si el número es 1-31 y NO hay am/pm/h y el contexto parece día del mes
            # («lunes 3 de agosto»), ya lo cubrió _SLOT_DAY_MONTH / DOM.
            if not ampm and 1 <= hour <= 31 and re.search(
                rf"{re.escape(m.group(0))}\s+de\s+({_MONTH_ALT})",
                text,
                re.I,
            ):
                pass
            else:
                return _next_weekday(wd, hour_n, minute)

    return None


def extract_pending_slot(history: list[dict[str, Any]]) -> datetime | None:
    """Busca hueco en mensajes recientes (asistente y usuario)."""
    for msg in reversed(history or []):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") not in ("assistant", "user"):
            continue
        slot = extract_slot_from_text(str(msg.get("content") or ""))
        if slot is not None:
            return slot
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


async def _book_slot(
    slot: datetime,
    client_context: dict[str, Any],
    *,
    reason: str,
) -> str:
    fecha_hora = slot.strftime("%Y-%m-%dT%H:%M")
    logger.info("booking_confirm: %s → agendar_cita %s", reason, fecha_hora)
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


async def try_confirm_pending_booking(
    user_text: str,
    history: list[dict[str, Any]],
    client_context: dict[str, Any],
) -> str | None:
    """Agenda en duro si el usuario afirma o trae día+hora claros.

    Returns:
        Respuesta lista para WhatsApp, o None si no aplica (seguir con el LLM).
    """
    raw = _strip_user_wrapper(user_text)

    # 1) Mensaje con día+hora claros («quiero el lunes a las 10»)
    if looks_like_booking_request(raw):
        slot = extract_slot_from_text(raw)
        if slot is not None:
            return await _book_slot(slot, client_context, reason="user_message_slot")

    # 2) Sí / ok → hueco del historial
    if is_user_affirmation(raw):
        slot = extract_pending_slot(history)
        if slot is None:
            logger.info(
                "booking_confirm: affirmation without parseable slot in history"
            )
            # No pasar al LLM: evita el bucle del fallback del guard.
            return (
                "Para guardarla dime el día y la hora en un solo mensaje, "
                "por ejemplo: lunes a las 10"
            )
        return await _book_slot(slot, client_context, reason="affirmation")

    return None
