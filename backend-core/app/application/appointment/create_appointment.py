"""Caso de uso: crear una cita (desde el bot o el panel)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.application.appointment.parsers import parse_datetime
from app.application.dtos import (
    AppointmentOutput,
    CreateAppointmentInput,
    appointment_to_output,
)
from app.domain.appointment.entity import (
    Appointment,
    BusinessSchedule,
    ensure_not_in_past,
)
from app.domain.appointment.repository import (
    AppointmentRepository,
    BusinessScheduleRepository,
)
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import (
    AppointmentOverlapError,
    InvalidAppointmentError,
    OutsideBusinessHoursError,
)
from app.domain.shared.phone import normalize_phone
from app.application.contact.ensure_contact_lead import (
    EnsureContactLeadInput,
    EnsureContactLeadUseCase,
)


class CreateAppointmentUseCase:
    """Orquesta la creación de una cita aplicando las reglas de agenda:

    1. La cita no puede estar en el pasado.
    2. Debe caer dentro del horario del negocio.
    3. No puede solaparse con otra cita activa del mismo negocio.
    4. CRM-4: si hay lead_repo, asegura ficha/lead del contacto (best-effort).
    """

    def __init__(
        self,
        repo: AppointmentRepository,
        schedule_repo: BusinessScheduleRepository,
        now_provider=None,
        lead_repo: LeadRepository | None = None,
    ) -> None:
        self._repo = repo
        self._schedule_repo = schedule_repo
        self._now = now_provider or (lambda: datetime.now(timezone.utc))
        self._lead_repo = lead_repo

    async def execute(self, input: CreateAppointmentInput) -> AppointmentOutput:
        if not input.client_id.strip():
            raise InvalidAppointmentError("client_id is required")
        if not input.contact_phone.strip():
            raise InvalidAppointmentError("contact_phone is required")

        schedule = (
            await self._schedule_repo.get_business_schedule(input.client_id)
            or BusinessSchedule.default()
        )

        starts_at = parse_datetime(input.starts_at, schedule.tzinfo)
        if input.ends_at:
            ends_at = parse_datetime(input.ends_at, schedule.tzinfo)
        else:
            ends_at = starts_at + timedelta(
                minutes=schedule.appointment_duration_minutes
            )

        ensure_not_in_past(starts_at, now=self._now())

        if not schedule.covers(starts_at, ends_at):
            raise OutsideBusinessHoursError(
                "Appointment is outside business hours"
            )

        overlapping = await self._repo.find_overlapping(
            client_id=input.client_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        if overlapping:
            raise AppointmentOverlapError(
                "Appointment overlaps with an existing appointment"
            )

        phone = normalize_phone(input.contact_phone) or input.contact_phone.strip()

        appointment = Appointment(
            client_id=UUID(input.client_id),
            conversation_id=UUID(input.conversation_id) if input.conversation_id else None,
            contact_phone=phone,
            contact_name=input.contact_name.strip(),
            starts_at=starts_at,
            ends_at=ends_at,
            notes=input.notes,
        )

        await self._repo.save(appointment)
        await self._ensure_contact_lead(
            client_id=input.client_id,
            phone=phone,
            name=input.contact_name.strip(),
        )
        return appointment_to_output(appointment)

    async def _ensure_contact_lead(
        self, client_id: str, phone: str, name: str
    ) -> None:
        if self._lead_repo is None:
            return
        try:
            await EnsureContactLeadUseCase(self._lead_repo).execute(
                EnsureContactLeadInput(
                    client_id=client_id,
                    phone=phone,
                    name=name,
                    source="appointment",
                )
            )
        except Exception:
            # CRM es best-effort: un fallo de lead NUNCA debe tumbar la cita.
            return
