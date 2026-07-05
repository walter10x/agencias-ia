"""Fakes in-memory de los puertos del módulo de agenda (para unit tests)."""

from __future__ import annotations

from datetime import datetime

from app.domain.appointment.entity import Appointment, BusinessSchedule
from app.domain.appointment.repository import (
    AppointmentRepository,
    BusinessScheduleRepository,
)


class FakeAppointmentRepository(AppointmentRepository):
    """Repositorio in-memory con la misma semántica que el adapter Supabase."""

    def __init__(self) -> None:
        self.items: dict[str, Appointment] = {}

    async def save(self, appointment: Appointment) -> None:
        self.items[str(appointment.id)] = appointment

    async def find_by_id(self, appointment_id: str):
        return self.items.get(appointment_id)

    def _filtered(
        self,
        client_id: str,
        date_from: datetime | None,
        date_to: datetime | None,
        status: str | None,
    ) -> list[Appointment]:
        result = [a for a in self.items.values() if str(a.client_id) == client_id]
        if date_from:
            result = [a for a in result if a.starts_at >= date_from]
        if date_to:
            result = [a for a in result if a.starts_at <= date_to]
        if status:
            result = [a for a in result if a.status.value == status]
        result.sort(key=lambda a: a.starts_at)
        return result

    async def list_by_client(
        self,
        client_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Appointment]:
        return self._filtered(client_id, date_from, date_to, status)[
            offset : offset + limit
        ]

    async def count_by_client(
        self,
        client_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
    ) -> int:
        return len(self._filtered(client_id, date_from, date_to, status))

    async def find_overlapping(
        self,
        client_id: str,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: str | None = None,
    ) -> list[Appointment]:
        return [
            a
            for a in self.items.values()
            if str(a.client_id) == client_id
            and (exclude_id is None or str(a.id) != exclude_id)
            and a.overlaps_range(starts_at, ends_at)
        ]

    async def find_next_by_phone(
        self,
        client_id: str,
        contact_phone: str,
        now: datetime,
    ):
        candidates = [
            a
            for a in self.items.values()
            if str(a.client_id) == client_id
            and a.contact_phone == contact_phone
            and a.is_active()
            and a.ends_at >= now
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda a: a.starts_at)


class FakeScheduleRepository(BusinessScheduleRepository):
    """Retorna siempre el mismo BusinessSchedule (configurable por test)."""

    def __init__(self, schedule: BusinessSchedule | None = None) -> None:
        self.schedule = schedule or BusinessSchedule.default()
        self.calls: list[str] = []

    async def get_business_schedule(self, client_id: str):
        self.calls.append(client_id)
        return self.schedule
