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

# Solo hora: «10 am», «10:00», «a las 10», «10am»
_TIME_ONLY = re.compile(
    r"^\s*(?:a\s+las?\s+|las?\s+)?"
    r"(\d{1,2})(?::(\d{2}))?\s*"
    r"(am|pm|h|hrs?|horas?)?\s*$",
    re.IGNORECASE,
)

_PENDING_DAY_MONTH = re.compile(
    rf"(\d{{1,2}})\s+de\s+({_MONTH_ALT})",
    re.IGNORECASE,
)
_PENDING_WEEKDAY = re.compile(rf"\b({_WEEKDAY_ALT})\b", re.IGNORECASE)
_PENDING_TOMORROW = re.compile(r"\bma[nñ]ana\b", re.IGNORECASE)


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


def extract_time_only(text: str) -> tuple[int, int] | None:
    """Si el mensaje es solo una hora («10 am»), devuelve (hour, minute)."""
    raw = _strip_user_wrapper(text)
    if not raw or len(raw) > 24:
        return None
    m = _TIME_ONLY.match(raw)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or "0")
    ampm = (m.group(3) or "").lower()
    if ampm in ("h", "hr", "hrs", "hora", "horas"):
        ampm = ""
    if ampm not in ("am", "pm"):
        ampm = _ampm_in(raw) or ""
    hour_n = _normalize_hour(hour, ampm or None)
    if hour_n is None or not (7 <= hour_n <= 21):
        return None
    if minute < 0 or minute > 59:
        return None
    return hour_n, minute


def extract_pending_day(history: list[dict[str, Any]]) -> date | None:
    """Día pendiente del chat (lunes / 3 de agosto / mañana), sin hora."""
    now = datetime.now(_TZ)
    for msg in reversed(history or []):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") not in ("assistant", "user"):
            continue
        content = str(msg.get("content") or "")
        if not content.strip() or _FALLBACK_GUARD.search(content):
            continue

        m = _PENDING_DAY_MONTH.search(content)
        if m:
            day = int(m.group(1))
            month = _MONTHS.get(m.group(2).lower())
            if month is None:
                continue
            try:
                candidate = date(now.year, month, day)
            except ValueError:
                continue
            if candidate < now.date():
                try:
                    candidate = date(now.year + 1, month, day)
                except ValueError:
                    continue
            return candidate

        if _PENDING_TOMORROW.search(content):
            return now.date() + timedelta(days=1)

        m = _PENDING_WEEKDAY.search(content)
        if m:
            wd = _weekday_index(m.group(1))
            if wd is None:
                continue
            days_ahead = (wd - now.weekday()) % 7
            candidate = now.date() + timedelta(days=days_ahead)
            # Si es hoy y ya pasó la mañana laboral, el siguiente de esa semana
            # se decide al combinar con la hora.
            return candidate

    return None


def combine_day_and_time(day: date, hour: int, minute: int) -> datetime:
    """Junta día + hora; si ya pasó, empuja 7 días cuando el día era weekday relativo."""
    now = datetime.now(_TZ)
    dt = datetime.combine(day, time(hour, minute), tzinfo=_TZ)
    if dt <= now:
        dt = dt + timedelta(days=7)
    return dt


def extract_pending_slot(history: list[dict[str, Any]]) -> datetime | None:
    """Busca hueco completo en mensajes recientes (asistente y usuario)."""
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
        return _humanize_tool_error(content)

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

    # 2) Solo hora («10 am») + día pendiente en el historial («lunes» / «3 de agosto»)
    time_only = extract_time_only(raw)
    if time_only is not None:
        pending_day = extract_pending_day(history)
        if pending_day is not None:
            hour, minute = time_only
            slot = combine_day_and_time(pending_day, hour, minute)
            return await _book_slot(slot, client_context, reason="time_plus_history_day")
        logger.info("booking_confirm: time-only without pending day in history")
        return (
            "Dime el día junto con la hora, por ejemplo: lunes a las 10"
        )

    # 3) Sí / ok → hueco del historial
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


# ---------------------------------------------------------------------------
# Mis citas / cancelar / reprogramar (mismo estilo determinista)
# ---------------------------------------------------------------------------

_LIST_INTENT = re.compile(
    r"(?:"
    r"qu[eé]\s+tengo\s+agendad"
    r"|mis\s+citas?"
    r"|para\s+cu[aá]ndo\s+(?:es\s+)?mi\s+cita"
    r"|cu[aá]ndo\s+(?:es|tengo)\s+mi\s+cita"
    r"|tengo\s+(?:alguna\s+)?cita"
    r"|ver\s+mi\s+cita"
    r")",
    re.IGNORECASE,
)

_CANCEL_INTENT = re.compile(
    r"(?:"
    r"cancel\w*"
    r"|anul\w*"
    r"|borra(?:r|me)?\s+(?:la\s+)?cita"
    r"|no\s+(?:puedo|voy\s+a\s+poder)\s+(?:ir|asistir)"
    r"|quita(?:me)?\s+(?:la\s+)?cita"
    r")",
    re.IGNORECASE,
)

_RESCHEDULE_INTENT = re.compile(
    r"(?:"
    r"reprogram\w*"
    r"|cambiar?\s+(?:la\s+)?cita"
    r"|cambiar?\s+(?:la\s+)?hora"
    r"|cambiar?\s+(?:el\s+)?d[ií]a"
    r"|pas[aá](?:me|r|nos)?\s+(?:la\s+cita\s+)?(?:al|a\s+el|para\s+el|a)\b"
    r"|mu[eé]ve(?:me)?\s+(?:la\s+)?cita"
    r"|otro\s+(?:d[ií]a|horario|hueco)"
    r")",
    re.IGNORECASE,
)


def _humanize_tool_error(content: str) -> str:
    low = (content or "").lower()
    if "overlap" in low or "ocupad" in low:
        return (
            "Ese hueco ya está ocupado. "
            "Dime otra hora o día de lunes a viernes."
        )
    if "outside business hours" in low or "fuera de horario" in low:
        return (
            "Esa hora está fuera de nuestro horario (lunes a viernes). "
            "Prueba otra hora laboral."
        )
    if "past" in low or "pasado" in low:
        return "Esa fecha/hora ya pasó. Dime un hueco futuro."
    return content.strip() if content.strip() else (
        "No pude completar la operación. Prueba de nuevo con día y hora."
    )


async def try_list_appointments(client_context: dict[str, Any]) -> str:
    result = await execute_tool("consultar_mis_citas", {}, client_context)
    text = str(result or "").strip()
    if not text or text.lower().startswith("error"):
        return "No pude consultar tus citas ahora. Inténtalo en un momento."
    return text


async def try_cancel_appointment(client_context: dict[str, Any]) -> str:
    result = await execute_tool("cancelar_cita", {}, client_context)
    text = str(result or "").strip()
    low = text.lower()
    if "cancelada correctamente" in low:
        return (
            f"✅ {text.split('Inform')[0].strip()}"
            if "Inform" in text
            else f"✅ {text}"
        )
    if "no se encontró" in low or "no encontr" in low:
        return "No tienes ninguna cita próxima para cancelar."
    return _humanize_tool_error(text)


async def try_reschedule_appointment(
    user_text: str,
    history: list[dict[str, Any]],
    client_context: dict[str, Any],
) -> str | None:
    """Reprograma si el mensaje trae (o el historial + hora) un nuevo hueco."""
    raw = _strip_user_wrapper(user_text)
    slot = extract_slot_from_text(raw)
    if slot is None:
        time_only = extract_time_only(raw)
        if time_only is not None:
            day = extract_pending_day(history)
            if day is not None:
                slot = combine_day_and_time(day, time_only[0], time_only[1])
    if slot is None:
        # Pidió reprogramar pero sin día/hora → pedir dato, no LLM
        return (
            "Claro. Dime el nuevo día y hora, por ejemplo: martes a las 11"
        )

    fecha_hora = slot.strftime("%Y-%m-%dT%H:%M")
    logger.info("booking_confirm: reprogramar → %s", fecha_hora)
    result = await execute_tool(
        "reprogramar_cita",
        {"nueva_fecha_hora": fecha_hora},
        client_context,
    )
    text = str(result or "").strip()
    low = text.lower()
    if "reprogramada correctamente" in low:
        return (
            f"✅ Cita reprogramada al {slot.strftime('%Y-%m-%d %H:%M')}. "
            "Queda actualizada en la agenda."
        )
    if "no encontr" in low:
        return (
            "No tienes una cita próxima para cambiar. "
            "Si quieres, agenda una nueva diciendo día y hora."
        )
    return _humanize_tool_error(text)


async def try_handle_agenda_intent(
    user_text: str,
    history: list[dict[str, Any]],
    client_context: dict[str, Any],
) -> str | None:
    """Enruta intents de agenda sin depender del LLM.

    Orden: cancelar → mis citas → reprogramar → agendar/confirmar.
    """
    raw = _strip_user_wrapper(user_text)
    if not raw:
        return None

    # Cancelar (antes que list, por si dicen "cancelar mi cita")
    if _CANCEL_INTENT.search(raw) and not _RESCHEDULE_INTENT.search(raw):
        # Evitar "no canceles" raros: si niegan, dejar al LLM
        if re.search(r"\bno\s+cancel", raw, re.I):
            return None
        return await try_cancel_appointment(client_context)

    if _LIST_INTENT.search(raw) and not _RESCHEDULE_INTENT.search(raw):
        return await try_list_appointments(client_context)

    if _RESCHEDULE_INTENT.search(raw):
        return await try_reschedule_appointment(raw, history, client_context)

    # Reprogramar implícito: "pásame al martes a las 11" ya cubierto por intent.
    # Si solo trae nuevo hueco y hay cita… lo deja el flujo de agendar (puede
    # solapar). Mejor: agendar/confirm path existente.
    return await try_confirm_pending_booking(raw, history, client_context)
