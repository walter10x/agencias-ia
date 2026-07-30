"""Caso de uso: actualizar horario de negocio de un tenant."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.appointment.get_business_hours import (
    BusinessHoursOutput,
    schedule_to_output,
)
from app.domain.appointment.entity import BusinessSchedule
from app.domain.appointment.repository import BusinessScheduleRepository
from app.domain.shared.errors import ClientNotFoundError, InvalidAppointmentError


@dataclass(frozen=True, slots=True)
class UpdateBusinessHoursInput:
    client_id: str
    timezone: str
    appointment_duration_minutes: int
    weekly: dict[str, list[list[str]]]
    reminder_offset_minutes: int = 1440


class UpdateBusinessHoursUseCase:
    def __init__(self, schedule_repo: BusinessScheduleRepository) -> None:
        self._repo = schedule_repo

    async def execute(self, input: UpdateBusinessHoursInput) -> BusinessHoursOutput:
        existing = await self._repo.get_business_schedule(input.client_id)
        if existing is None:
            raise ClientNotFoundError(f"Client not found: {input.client_id}")

        weekly_hours: dict[str, list[tuple[str, str]]] = {}
        for day, ranges in input.weekly.items():
            parsed: list[tuple[str, str]] = []
            for item in ranges or []:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise InvalidAppointmentError(
                        f"Invalid range for {day}: expected [HH:MM, HH:MM]"
                    )
                parsed.append((str(item[0]), str(item[1])))
            weekly_hours[str(day).lower()] = parsed

        try:
            schedule = BusinessSchedule(
                weekly_hours=weekly_hours,
                appointment_duration_minutes=input.appointment_duration_minutes,
                timezone=input.timezone.strip() or "UTC",
                reminder_offset_minutes=input.reminder_offset_minutes,
            )
        except InvalidAppointmentError:
            raise
        except Exception as exc:  # noqa: BLE001 — mapear a dominio
            raise InvalidAppointmentError(str(exc)) from exc

        saved = await self._repo.save_business_schedule(input.client_id, schedule)
        return schedule_to_output(input.client_id, saved)
