"""Caso de uso: leer horario de negocio de un tenant."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.appointment.entity import BusinessSchedule
from app.domain.appointment.repository import BusinessScheduleRepository
from app.domain.shared.errors import ClientNotFoundError


@dataclass(frozen=True, slots=True)
class GetBusinessHoursInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class BusinessHoursOutput:
    client_id: str
    timezone: str
    appointment_duration_minutes: int
    reminder_offset_minutes: int
    weekly: dict[str, list[list[str]]]


def schedule_to_output(client_id: str, schedule: BusinessSchedule) -> BusinessHoursOutput:
    weekly = {
        day: [[start, end] for start, end in ranges]
        for day, ranges in schedule.weekly_hours.items()
    }
    return BusinessHoursOutput(
        client_id=client_id,
        timezone=schedule.timezone,
        appointment_duration_minutes=schedule.appointment_duration_minutes,
        reminder_offset_minutes=schedule.reminder_offset_minutes,
        weekly=weekly,
    )


class GetBusinessHoursUseCase:
    def __init__(self, schedule_repo: BusinessScheduleRepository) -> None:
        self._repo = schedule_repo

    async def execute(self, input: GetBusinessHoursInput) -> BusinessHoursOutput:
        schedule = await self._repo.get_business_schedule(input.client_id)
        if schedule is None:
            raise ClientNotFoundError(f"Client not found: {input.client_id}")
        return schedule_to_output(input.client_id, schedule)
