"""Entidades del módulo de agenda.

Appointment: entidad raíz de una cita agendada.
AppointmentStatus: enum con los estados de la cita.
BusinessSchedule: value object con el horario semanal del negocio
                  y la duración de cita por defecto.

Reglas de dominio:
- Una cita siempre termina después de empezar (ends_at > starts_at).
- Dos citas activas (pending/confirmed) del mismo negocio no pueden solaparse.
- Una cita nueva debe estar dentro del horario del negocio y no en el pasado
  (reglas aplicadas por los use cases con los helpers de este módulo).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.domain.shared.errors import InvalidAppointmentError


class AppointmentStatus(str, Enum):
    """Estados del ciclo de vida de una cita."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    @classmethod
    def valid_statuses(cls) -> frozenset[str]:
        return frozenset(s.value for s in cls)

    @classmethod
    def blocking_statuses(cls) -> frozenset[AppointmentStatus]:
        """Estados que ocupan el slot (bloquean disponibilidad)."""
        return frozenset({cls.PENDING, cls.CONFIRMED})


# Días de la semana en el orden de datetime.weekday()
WEEKDAY_KEYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

DEFAULT_WEEKLY_HOURS: dict[str, list[tuple[str, str]]] = {
    "monday": [("09:00", "18:00")],
    "tuesday": [("09:00", "18:00")],
    "wednesday": [("09:00", "18:00")],
    "thursday": [("09:00", "18:00")],
    "friday": [("09:00", "18:00")],
    "saturday": [],
    "sunday": [],
}

DEFAULT_APPOINTMENT_DURATION_MINUTES = 30


def _parse_hhmm(value: str) -> time:
    """Parsea 'HH:MM' a datetime.time. Lanza InvalidAppointmentError si es inválido."""
    try:
        hour, minute = value.strip().split(":")
        return time(int(hour), int(minute))
    except (ValueError, AttributeError) as exc:
        raise InvalidAppointmentError(f"Invalid time format: {value!r} (expected HH:MM)") from exc


@dataclass(frozen=True)
class BusinessSchedule:
    """Horario semanal del negocio + duración de cita por defecto.

    weekly_hours: {"monday": [("09:00", "13:00"), ("15:00", "19:00")], ...}
    Un día sin rangos (lista vacía o ausente) significa cerrado.
    """

    weekly_hours: dict[str, list[tuple[str, str]]] = field(
        default_factory=lambda: dict(DEFAULT_WEEKLY_HOURS)
    )
    appointment_duration_minutes: int = DEFAULT_APPOINTMENT_DURATION_MINUTES
    timezone: str = "UTC"

    def __post_init__(self) -> None:
        if not (5 <= self.appointment_duration_minutes <= 480):
            raise InvalidAppointmentError(
                "appointment_duration_minutes must be between 5 and 480"
            )
        try:
            ZoneInfo(self.timezone)
        except Exception as exc:
            raise InvalidAppointmentError(f"Invalid timezone: {self.timezone!r}") from exc

    @classmethod
    def default(cls) -> BusinessSchedule:
        return cls()

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def ranges_for(self, day: date) -> list[tuple[time, time]]:
        """Rangos de apertura (hora local del negocio) para un día concreto."""
        key = WEEKDAY_KEYS[day.weekday()]
        ranges: list[tuple[time, time]] = []
        for raw_start, raw_end in self.weekly_hours.get(key, []):
            start_t = _parse_hhmm(raw_start)
            end_t = _parse_hhmm(raw_end)
            if end_t <= start_t:
                raise InvalidAppointmentError(
                    f"Invalid business hours range for {key}: {raw_start}-{raw_end}"
                )
            ranges.append((start_t, end_t))
        return sorted(ranges)

    def covers(self, starts_at: datetime, ends_at: datetime) -> bool:
        """True si el rango [starts_at, ends_at) cae dentro del horario del negocio.

        Los datetimes deben ser timezone-aware; se convierten a la zona
        horaria del negocio antes de comparar. Las citas no pueden cruzar
        de un día a otro (MVP).
        """
        local_start = starts_at.astimezone(self.tzinfo)
        local_end = ends_at.astimezone(self.tzinfo)
        if local_start.date() != local_end.date():
            return False
        for range_start, range_end in self.ranges_for(local_start.date()):
            if local_start.time() >= range_start and local_end.time() <= range_end:
                return True
        return False


def ensure_not_in_past(starts_at: datetime, now: datetime | None = None) -> None:
    """Regla de dominio: no se agendan citas en el pasado."""
    reference = now or datetime.now(timezone.utc)
    if starts_at < reference:
        raise InvalidAppointmentError("Cannot schedule an appointment in the past")


@dataclass
class Appointment:
    """Entidad que representa una cita agendada para un negocio (tenant).

    Invariantes:
    - client_id no puede ser nulo
    - contact_phone no puede estar vacío
    - ends_at debe ser posterior a starts_at
    - status debe ser un valor válido de AppointmentStatus
    """

    id: UUID = field(default_factory=uuid4)
    client_id: UUID = field(default_factory=uuid4)
    conversation_id: UUID | None = None
    contact_phone: str = ""
    contact_name: str = ""
    starts_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ends_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=30)
    )
    status: AppointmentStatus = AppointmentStatus.PENDING
    notes: str = ""
    reminder_sent_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.contact_phone.strip():
            raise InvalidAppointmentError("Appointment contact_phone cannot be empty")
        if isinstance(self.status, str) and not isinstance(self.status, AppointmentStatus):
            try:
                self.status = AppointmentStatus(self.status)
            except ValueError:
                raise InvalidAppointmentError(
                    f"Invalid status: {self.status}. "
                    f"Valid: {sorted(AppointmentStatus.valid_statuses())}"
                )
        if self.ends_at <= self.starts_at:
            raise InvalidAppointmentError("Appointment ends_at must be after starts_at")

    # ------------------------------------------------------------------
    # Reglas de negocio
    # ------------------------------------------------------------------

    def is_active(self) -> bool:
        """True si la cita ocupa su slot (pending o confirmed)."""
        return self.status in AppointmentStatus.blocking_statuses()

    def overlaps_range(self, starts_at: datetime, ends_at: datetime) -> bool:
        """True si esta cita (activa) se solapa con el rango dado.

        Dos rangos se solapan si empiezan antes de que el otro termine.
        Citas canceladas o completadas no bloquean.
        """
        if not self.is_active():
            return False
        return self.starts_at < ends_at and starts_at < self.ends_at

    def overlaps(self, other: Appointment) -> bool:
        """True si ambas citas activas del mismo negocio se solapan."""
        if self.client_id != other.client_id:
            return False
        if not other.is_active():
            return False
        return self.overlaps_range(other.starts_at, other.ends_at)

    def confirm(self) -> None:
        """Confirma una cita pendiente."""
        if self.status != AppointmentStatus.PENDING:
            raise InvalidAppointmentError(
                f"Only pending appointments can be confirmed (status={self.status.value})"
            )
        self.status = AppointmentStatus.CONFIRMED
        self.updated_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """Cancela la cita. No se puede cancelar dos veces ni cancelar una completada."""
        if self.status == AppointmentStatus.CANCELLED:
            raise InvalidAppointmentError("Appointment is already cancelled")
        if self.status == AppointmentStatus.COMPLETED:
            raise InvalidAppointmentError("Cannot cancel a completed appointment")
        self.status = AppointmentStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        """Marca la cita como completada (asistió)."""
        if not self.is_active():
            raise InvalidAppointmentError(
                f"Only active appointments can be completed (status={self.status.value})"
            )
        self.status = AppointmentStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def reschedule(self, new_starts_at: datetime, new_ends_at: datetime) -> None:
        """Reprograma la cita a un nuevo rango. Solo citas activas."""
        if not self.is_active():
            raise InvalidAppointmentError(
                f"Cannot reschedule a {self.status.value} appointment"
            )
        if new_ends_at <= new_starts_at:
            raise InvalidAppointmentError("Appointment ends_at must be after starts_at")
        self.starts_at = new_starts_at
        self.ends_at = new_ends_at
        # Un cambio de fecha invalida el recordatorio ya enviado
        self.reminder_sent_at = None
        self.updated_at = datetime.now(timezone.utc)

    def mark_reminder_sent(self) -> None:
        """Registra que se envió el recordatorio (Fase 4)."""
        self.reminder_sent_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def update_notes(self, notes: str) -> None:
        self.notes = notes
        self.updated_at = datetime.now(timezone.utc)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Appointment):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
