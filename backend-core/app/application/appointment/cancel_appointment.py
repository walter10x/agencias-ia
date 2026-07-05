"""Caso de uso: cancelar una cita (scoped por tenant)."""

from __future__ import annotations

from app.application.dtos import (
    AppointmentOutput,
    CancelAppointmentInput,
    appointment_to_output,
)
from app.domain.appointment.repository import AppointmentRepository
from app.domain.shared.errors import AppointmentNotFoundError, InvalidAppointmentError


class CancelAppointmentUseCase:
    """Cancela una cita verificando que pertenece al tenant.

    Si la cita no existe o pertenece a otro cliente, lanza
    AppointmentNotFoundError (no se filtra información entre tenants).
    """

    def __init__(self, repo: AppointmentRepository) -> None:
        self._repo = repo

    async def execute(self, input: CancelAppointmentInput) -> AppointmentOutput:
        if not input.appointment_id.strip():
            raise InvalidAppointmentError("appointment_id is required")

        appointment = await self._repo.find_by_id(input.appointment_id)
        if appointment is None or str(appointment.client_id) != input.client_id:
            raise AppointmentNotFoundError(
                f"Appointment not found: {input.appointment_id}"
            )

        appointment.cancel()
        await self._repo.save(appointment)
        return appointment_to_output(appointment)
