"""Caso de uso: reprogramar una cita existente."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.application.appointment.parsers import parse_datetime
from app.application.dtos import (
    AppointmentOutput,
    RescheduleAppointmentInput,
    appointment_to_output,
)
from app.domain.appointment.entity import BusinessSchedule, ensure_not_in_past
from app.domain.appointment.repository import (
    AppointmentRepository,
    BusinessScheduleRepository,
)
from app.domain.shared.errors import (
    AppointmentNotFoundError,
    AppointmentOverlapError,
    InvalidAppointmentError,
    OutsideBusinessHoursError,
)


class RescheduleAppointmentUseCase:
    """Reprograma una cita aplicando las mismas reglas que la creación:
    no en el pasado, dentro de horario y sin solapes (excluyéndose a sí misma).
    """

    def __init__(
        self,
        repo: AppointmentRepository,
        schedule_repo: BusinessScheduleRepository,
        now_provider=None,
    ) -> None:
        self._repo = repo
        self._schedule_repo = schedule_repo
        self._now = now_provider or (lambda: datetime.now(timezone.utc))

    async def execute(self, input: RescheduleAppointmentInput) -> AppointmentOutput:
        if not input.appointment_id.strip():
            raise InvalidAppointmentError("appointment_id is required")

        appointment = await self._repo.find_by_id(input.appointment_id)
        if appointment is None or str(appointment.client_id) != input.client_id:
            raise AppointmentNotFoundError(
                f"Appointment not found: {input.appointment_id}"
            )

        schedule = (
            await self._schedule_repo.get_business_schedule(input.client_id)
            or BusinessSchedule.default()
        )

        new_starts_at = parse_datetime(input.new_starts_at, schedule.tzinfo)
        if input.new_ends_at:
            new_ends_at = parse_datetime(input.new_ends_at, schedule.tzinfo)
        else:
            duration = appointment.ends_at - appointment.starts_at
            if duration <= timedelta(0):
                duration = timedelta(minutes=schedule.appointment_duration_minutes)
            new_ends_at = new_starts_at + duration

        ensure_not_in_past(new_starts_at, now=self._now())

        if not schedule.covers(new_starts_at, new_ends_at):
            raise OutsideBusinessHoursError("Appointment is outside business hours")

        overlapping = await self._repo.find_overlapping(
            client_id=input.client_id,
            starts_at=new_starts_at,
            ends_at=new_ends_at,
            exclude_id=str(appointment.id),
        )
        if overlapping:
            raise AppointmentOverlapError(
                "Appointment overlaps with an existing appointment"
            )

        appointment.reschedule(new_starts_at, new_ends_at)
        await self._repo.save(appointment)
        return appointment_to_output(appointment)
