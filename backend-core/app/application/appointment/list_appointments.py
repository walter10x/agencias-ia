"""Caso de uso: listar citas de un cliente con filtros por fecha y estado."""

from __future__ import annotations

from app.application.appointment.parsers import parse_optional_boundary
from app.application.dtos import (
    AppointmentOutput,
    ListAppointmentsInput,
    appointment_to_output,
)
from app.domain.appointment.entity import AppointmentStatus, BusinessSchedule
from app.domain.appointment.repository import (
    AppointmentRepository,
    BusinessScheduleRepository,
)
from app.domain.shared.errors import InvalidAppointmentError


class ListAppointmentsUseCase:
    """Lista citas scoped por tenant, con filtros opcionales de fecha y estado."""

    def __init__(
        self,
        repo: AppointmentRepository,
        schedule_repo: BusinessScheduleRepository | None = None,
    ) -> None:
        self._repo = repo
        self._schedule_repo = schedule_repo

    async def execute(
        self, input: ListAppointmentsInput
    ) -> tuple[list[AppointmentOutput], int]:
        if not input.client_id.strip():
            raise InvalidAppointmentError("client_id is required")
        if input.status is not None and input.status not in AppointmentStatus.valid_statuses():
            raise InvalidAppointmentError(
                f"Invalid status: {input.status}. "
                f"Valid: {sorted(AppointmentStatus.valid_statuses())}"
            )
        if input.limit < 1:
            raise InvalidAppointmentError("limit must be >= 1")
        if input.offset < 0:
            raise InvalidAppointmentError("offset must be >= 0")

        schedule = None
        if self._schedule_repo is not None:
            schedule = await self._schedule_repo.get_business_schedule(input.client_id)
        schedule = schedule or BusinessSchedule.default()

        date_from = parse_optional_boundary(input.date_from, schedule.tzinfo)
        date_to = parse_optional_boundary(input.date_to, schedule.tzinfo, end=True)

        appointments = await self._repo.list_by_client(
            client_id=input.client_id,
            date_from=date_from,
            date_to=date_to,
            status=input.status,
            limit=input.limit,
            offset=input.offset,
        )
        total = await self._repo.count_by_client(
            client_id=input.client_id,
            date_from=date_from,
            date_to=date_to,
            status=input.status,
        )
        return [appointment_to_output(a) for a in appointments], total
