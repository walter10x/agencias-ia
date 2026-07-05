"""Caso de uso: slots libres de un día según business_hours y citas existentes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.application.appointment.parsers import parse_date
from app.application.dtos import (
    AvailabilityOutput,
    AvailabilitySlotOutput,
    GetAvailabilityInput,
)
from app.domain.appointment.entity import BusinessSchedule
from app.domain.appointment.repository import (
    AppointmentRepository,
    BusinessScheduleRepository,
)
from app.domain.shared.errors import InvalidAppointmentError


class GetAvailabilityUseCase:
    """Calcula los slots libres de un día:

    1. Genera slots de `appointment_duration_minutes` dentro de cada rango
       del horario del negocio (hora local del negocio).
    2. Descarta slots que se solapan con citas activas existentes.
    3. Descarta slots que ya pasaron (si la fecha es hoy).
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

    async def execute(self, input: GetAvailabilityInput) -> AvailabilityOutput:
        if not input.client_id.strip():
            raise InvalidAppointmentError("client_id is required")

        day = parse_date(input.date)
        schedule = (
            await self._schedule_repo.get_business_schedule(input.client_id)
            or BusinessSchedule.default()
        )
        tz = schedule.tzinfo
        duration = timedelta(minutes=schedule.appointment_duration_minutes)
        now = self._now()

        # Límites del día en la zona del negocio, convertidos a UTC
        day_start = datetime(day.year, day.month, day.day, tzinfo=tz)
        day_end = day_start + timedelta(days=1)

        appointments = await self._repo.list_by_client(
            client_id=input.client_id,
            date_from=day_start.astimezone(timezone.utc),
            date_to=day_end.astimezone(timezone.utc),
            limit=500,
        )
        busy = [a for a in appointments if a.is_active()]

        slots: list[AvailabilitySlotOutput] = []
        for range_start, range_end in schedule.ranges_for(day):
            cursor = datetime.combine(day, range_start, tzinfo=tz)
            range_limit = datetime.combine(day, range_end, tzinfo=tz)
            while cursor + duration <= range_limit:
                slot_start = cursor.astimezone(timezone.utc)
                slot_end = (cursor + duration).astimezone(timezone.utc)
                if slot_start >= now and not any(
                    a.overlaps_range(slot_start, slot_end) for a in busy
                ):
                    slots.append(
                        AvailabilitySlotOutput(
                            starts_at=slot_start.isoformat(),
                            ends_at=slot_end.isoformat(),
                            label=cursor.strftime("%H:%M"),
                        )
                    )
                cursor += duration

        return AvailabilityOutput(
            date=day.isoformat(),
            timezone=schedule.timezone,
            slot_duration_minutes=schedule.appointment_duration_minutes,
            slots=slots,
        )
