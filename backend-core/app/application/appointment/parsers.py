"""Helpers de parsing de fechas para los use cases de agenda."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.domain.shared.errors import InvalidAppointmentError

_ACCEPTED_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M",
)


def parse_datetime(value: str, business_tz: ZoneInfo) -> datetime:
    """Parsea un datetime ISO (u otros formatos comunes) a datetime aware en UTC.

    Si el valor es naive (sin offset), se interpreta en la zona horaria
    del negocio — es lo que un usuario de WhatsApp quiere decir con
    "mañana a las 10".
    """
    raw = (value or "").strip()
    if not raw:
        raise InvalidAppointmentError("Datetime value is required")

    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        for fmt in _ACCEPTED_FORMATS:
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        raise InvalidAppointmentError(
            f"Invalid datetime format: {raw!r} (expected ISO 8601, e.g. 2026-07-10T15:00)"
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=business_tz)
    return parsed.astimezone(timezone.utc)


def parse_date(value: str) -> date:
    """Parsea una fecha YYYY-MM-DD."""
    raw = (value or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidAppointmentError(
            f"Invalid date format: {raw!r} (expected YYYY-MM-DD)"
        ) from exc


def parse_optional_boundary(value: str | None, business_tz: ZoneInfo, *, end: bool = False) -> datetime | None:
    """Parsea un filtro de fecha opcional (date o datetime) a datetime UTC.

    Un valor tipo fecha (YYYY-MM-DD) se expande al inicio (00:00) o al
    final (23:59:59.999999) del día en la zona del negocio.
    """
    if value is None or not value.strip():
        return None
    raw = value.strip()
    if len(raw) == 10:  # YYYY-MM-DD
        day = parse_date(raw)
        base = datetime(day.year, day.month, day.day, tzinfo=business_tz)
        if end:
            base = base.replace(hour=23, minute=59, second=59, microsecond=999999)
        return base.astimezone(timezone.utc)
    return parse_datetime(raw, business_tz)
