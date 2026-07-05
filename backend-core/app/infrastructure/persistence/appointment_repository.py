"""Supabase adapter for AppointmentRepository port (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.appointment.entity import Appointment, AppointmentStatus
from app.domain.appointment.repository import AppointmentRepository
from app.domain.shared.errors import DomainError
from app.infrastructure.http.supabase_client import SupabaseHttpClient


class SupabaseAppointmentRepository(AppointmentRepository):
    """Supabase implementation of AppointmentRepository."""

    TABLE = "appointments"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    async def save(self, appointment: Appointment) -> None:
        row = {
            "id": str(appointment.id),
            "client_id": str(appointment.client_id),
            "conversation_id": (
                str(appointment.conversation_id) if appointment.conversation_id else None
            ),
            "contact_phone": appointment.contact_phone,
            "contact_name": appointment.contact_name,
            "starts_at": appointment.starts_at.isoformat(),
            "ends_at": appointment.ends_at.isoformat(),
            "status": (
                appointment.status.value
                if isinstance(appointment.status, AppointmentStatus)
                else appointment.status
            ),
            "notes": appointment.notes,
            "reminder_sent_at": (
                appointment.reminder_sent_at.isoformat()
                if appointment.reminder_sent_at
                else None
            ),
            "created_at": appointment.created_at.isoformat(),
            "updated_at": appointment.updated_at.isoformat(),
        }
        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .upsert(row, on_conflict="id")
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)

    async def find_by_id(self, appointment_id: str) -> Optional[Appointment]:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("id", appointment_id)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_appointment(result.data[0])

    async def list_by_client(
        self,
        client_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Appointment]:
        try:
            query = (
                self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .order("starts_at")
                .limit(limit)
                .offset(offset)
            )
            if date_from:
                query = query.gte("starts_at", date_from.isoformat())
            if date_to:
                query = query.lte("starts_at", date_to.isoformat())
            if status:
                query = query.eq("status", status)

            result = await asyncio.to_thread(lambda: query.execute())
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_appointment(row) for row in result.data]

    async def count_by_client(
        self,
        client_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
    ) -> int:
        try:
            query = (
                self._db.table(self.TABLE)
                .select("id")
                .eq("client_id", client_id)
            )
            if date_from:
                query = query.gte("starts_at", date_from.isoformat())
            if date_to:
                query = query.lte("starts_at", date_to.isoformat())
            if status:
                query = query.eq("status", status)

            result = await asyncio.to_thread(lambda: query.execute())
            return len(result.data)
        except Exception as exc:
            self._raise_domain_error(exc)
            return 0

    async def find_overlapping(
        self,
        client_id: str,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: str | None = None,
    ) -> list[Appointment]:
        # Solape de rangos: existente.starts_at < nuevo.ends_at
        #                   AND existente.ends_at > nuevo.starts_at
        blocking = sorted(s.value for s in AppointmentStatus.blocking_statuses())
        try:
            query = (
                self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .lt("starts_at", ends_at.isoformat())
                .gt("ends_at", starts_at.isoformat())
                .in_("status", blocking)
            )
            if exclude_id:
                query = query.neq("id", exclude_id)

            result = await asyncio.to_thread(lambda: query.execute())
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_appointment(row) for row in result.data]

    async def find_next_by_phone(
        self,
        client_id: str,
        contact_phone: str,
        now: datetime,
    ) -> Optional[Appointment]:
        blocking = sorted(s.value for s in AppointmentStatus.blocking_statuses())
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .eq("contact_phone", contact_phone)
                .gte("ends_at", now.isoformat())
                .in_("status", blocking)
                .order("starts_at")
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_appointment(result.data[0])

    @staticmethod
    def _row_to_appointment(row: dict) -> Appointment:
        appt = Appointment(
            id=UUID(row["id"]),
            client_id=UUID(row["client_id"]),
            conversation_id=(
                UUID(row["conversation_id"]) if row.get("conversation_id") else None
            ),
            contact_phone=row["contact_phone"],
            contact_name=row.get("contact_name", "") or "",
            starts_at=datetime.fromisoformat(row["starts_at"]),
            ends_at=datetime.fromisoformat(row["ends_at"]),
            status=AppointmentStatus(row["status"]),
            notes=row.get("notes", "") or "",
        )
        if row.get("reminder_sent_at"):
            appt.reminder_sent_at = datetime.fromisoformat(row["reminder_sent_at"])
        appt.created_at = datetime.fromisoformat(row["created_at"])
        appt.updated_at = datetime.fromisoformat(row["updated_at"])
        return appt

    @staticmethod
    def _raise_domain_error(exc: Exception) -> None:
        import json

        import httpx

        message = str(exc)
        try:
            if "Supabase error:" in message:
                body_str = message.split("Supabase error:", 1)[1].strip()
                body = json.loads(body_str)
                message = body.get("message", message)
        except (json.JSONDecodeError, IndexError):
            pass

        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            raise DomainError("Database connection failed") from exc
        if "connection" in message.lower() or "timeout" in message.lower():
            raise DomainError("Database connection failed") from exc

        raise DomainError(f"Database error: {message}") from exc
