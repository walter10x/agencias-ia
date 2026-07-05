"""Supabase adapter for ClientRepository port (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from app.infrastructure.http.supabase_client import SupabaseHttpClient

from app.domain.appointment.entity import (
    DEFAULT_APPOINTMENT_DURATION_MINUTES,
    BusinessSchedule,
)
from app.domain.appointment.repository import BusinessScheduleRepository
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import DomainError, InvalidClientError
from app.domain.shared.value_objects import BusinessType, ClientId, Email, PasswordHash, WhatsAppNumber


class SupabaseClientRepository(ClientRepository, BusinessScheduleRepository):
    """Supabase implementation of ClientRepository.

    Uses supabase-py sync client wrapped in asyncio.to_thread.
    """

    TABLE = "clients"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    # ------------------------------------------------------------------
    # Port methods
    # ------------------------------------------------------------------

    async def save(self, client: Client) -> None:
        """Insert or update a Client (UPSERT by id)."""
        row = self._client_to_row(client)
        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .upsert(row, on_conflict="id")
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)

    async def find_by_id(self, client_id: ClientId) -> Optional[Client]:
        """Find a client by its ClientId. Returns None if not found."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("id", str(client_id))
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_client(result.data[0])

    async def find_by_whatsapp(self, number: str) -> Optional[Client]:
        """Find a client by WhatsApp number. Validates format first."""
        self._validate_whatsapp(number)

        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("whatsapp_number", number)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_client(result.data[0])

    async def find_by_email(self, email: Email) -> Optional[Client]:
        """Find a client by email. Returns None if not found."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("email", str(email))
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_client(result.data[0])

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Client]:
        """List active clients with pagination."""
        if limit < 1:
            raise InvalidClientError("limit must be >= 1")
        if offset < 0:
            raise InvalidClientError("offset must be >= 0")

        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("is_active", True)
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_client(row) for row in result.data]

    # ------------------------------------------------------------------
    # BusinessScheduleRepository port (módulo de agenda — solo lectura)
    # ------------------------------------------------------------------

    async def get_business_schedule(self, client_id: str) -> Optional[BusinessSchedule]:
        """Lee el horario del negocio desde las columnas de config del tenant.

        Retorna None si el cliente no existe. Si las columnas vienen
        vacías o con formato inesperado, retorna el horario por defecto
        para no romper la agenda.
        """
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("id,business_hours,appointment_duration_minutes")
                .eq("id", client_id)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_schedule(result.data[0])

    @staticmethod
    def _row_to_schedule(row: dict) -> BusinessSchedule:
        raw = row.get("business_hours") or {}
        if not isinstance(raw, dict):
            raw = {}
        weekly_raw = raw.get("weekly") or {}
        weekly: dict[str, list[tuple[str, str]]] = {}
        for day, ranges in weekly_raw.items():
            parsed_ranges: list[tuple[str, str]] = []
            for item in ranges or []:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    parsed_ranges.append((str(item[0]), str(item[1])))
            weekly[str(day).lower()] = parsed_ranges

        kwargs: dict = {
            "appointment_duration_minutes": int(
                row.get("appointment_duration_minutes")
                or DEFAULT_APPOINTMENT_DURATION_MINUTES
            ),
            "timezone": str(raw.get("timezone") or "UTC"),
        }
        if weekly:
            kwargs["weekly_hours"] = weekly
        return BusinessSchedule(**kwargs)

    # ------------------------------------------------------------------
    # Private mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _client_to_row(client: Client) -> dict:
        """Map a Client entity to a Supabase row dict."""
        row: dict[str, object] = {
            "id": str(client.id),
            "name": client.name,
            "business_type": str(client.business_type),
            "whatsapp_number": str(client.whatsapp_number),
            "is_active": client.is_active,
            "created_at": client.created_at.isoformat(),
            "updated_at": client.updated_at.isoformat(),
        }
        if client.email is not None:
            row["email"] = str(client.email)
        if client.password_hash is not None:
            row["password_hash"] = str(client.password_hash)
        row["role"] = client.role.value
        row["status"] = client.status.value
        row["phone_number_id"] = client.phone_number_id
        row["whatsapp_connected"] = client.whatsapp_connected
        row["plan"] = client.plan
        return row

    @staticmethod
    def _row_to_client(row: dict) -> Client:
        """Reconstruct a Client entity from a Supabase row dict."""
        client = Client(
            id=UUID(row["id"]),
            name=row["name"],
            business_type=BusinessType(row["business_type"]),
            whatsapp_number=WhatsAppNumber(row["whatsapp_number"]),
            is_active=row["is_active"],
        )
        if row.get("email"):
            object.__setattr__(client, "email", Email(row["email"]))
        if row.get("password_hash"):
            object.__setattr__(client, "password_hash", PasswordHash(row["password_hash"]))
        if row.get("role"):
            from app.domain.client.enums import ClientRole
            client.role = ClientRole(row["role"])
        if row.get("status"):
            from app.domain.client.enums import ClientStatus
            client.status = ClientStatus(row["status"])
        if row.get("phone_number_id"):
            client.phone_number_id = str(row["phone_number_id"])
        if row.get("whatsapp_connected"):
            client.whatsapp_connected = bool(row["whatsapp_connected"])
        if row.get("plan"):
            client.plan = str(row["plan"])
        client.created_at = datetime.fromisoformat(row["created_at"])
        client.updated_at = datetime.fromisoformat(row["updated_at"])
        return client

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_whatsapp(number: str) -> None:
        """Raise InvalidClientError if the WhatsApp format is invalid."""
        try:
            WhatsAppNumber(number)
        except ValueError as exc:
            raise InvalidClientError(str(exc)) from exc

    @staticmethod
    def _raise_domain_error(exc: Exception) -> None:
        """Map infrastructure exceptions to domain errors."""
        import json

        message = str(exc)

        # Try to parse Supabase PostgREST error from message body
        pg_code = ""
        try:
            if "Supabase error:" in message:
                body_str = message.split("Supabase error:", 1)[1].strip()
                body = json.loads(body_str)
                pg_code = body.get("code", "")
                message = body.get("message", message)
        except (json.JSONDecodeError, IndexError):
            pass

        # PostgreSQL unique_violation (23505) → duplicate WhatsApp
        if pg_code == "23505":
            raise InvalidClientError("WhatsApp number already registered") from exc

        # Connection / timeout errors
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            raise DomainError("Database connection failed") from exc
        if "connection" in message.lower() or "timeout" in message.lower():
            raise DomainError("Database connection failed") from exc

        raise DomainError(f"Database error: {message}") from exc
