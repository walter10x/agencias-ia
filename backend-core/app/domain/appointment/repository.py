"""Puertos de repositorio para el módulo de agenda (DRIVEN PORTS)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.domain.appointment.entity import Appointment, BusinessSchedule


class AppointmentRepository(ABC):
    """Interfaz de repositorio para el agregado Appointment.

    Se implementa en infrastructure/persistence/.
    El dominio no conoce Supabase ni SQL.
    """

    @abstractmethod
    async def save(self, appointment: Appointment) -> None:
        """Persiste una cita (crear o actualizar). Upsert por id."""
        ...

    @abstractmethod
    async def find_by_id(self, appointment_id: str) -> Optional[Appointment]:
        """Busca una cita por ID. Retorna None si no existe."""
        ...

    @abstractmethod
    async def list_by_client(
        self,
        client_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Appointment]:
        """Lista citas de un cliente, filtradas por rango de fecha y estado.

        date_from/date_to filtran sobre starts_at. Ordenadas por starts_at ASC.
        """
        ...

    @abstractmethod
    async def count_by_client(
        self,
        client_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
    ) -> int:
        """Cuenta citas de un cliente con los mismos filtros que list_by_client."""
        ...

    @abstractmethod
    async def find_overlapping(
        self,
        client_id: str,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: str | None = None,
    ) -> list[Appointment]:
        """Citas ACTIVAS (pending/confirmed) del cliente que se solapan con el rango.

        exclude_id permite omitir la propia cita al reprogramar.
        """
        ...

    @abstractmethod
    async def find_next_by_phone(
        self,
        client_id: str,
        contact_phone: str,
        now: datetime,
    ) -> Optional[Appointment]:
        """Próxima cita activa de un contacto (para cancelar desde el bot)."""
        ...

    @abstractmethod
    async def find_reminder_candidates(
        self,
        starts_from: datetime,
        starts_to: datetime,
    ) -> list[Appointment]:
        """Citas candidatas a recordatorio (Fase 4), CROSS-TENANT.

        Retorna citas con status in (pending, confirmed),
        reminder_sent_at IS NULL, y starts_at en [starts_from, starts_to).

        El rango es deliberadamente amplio (ver
        app.infrastructure.celery.reminders): el offset de recordatorio
        es configurable por cliente (JSONB de `clients`), así que no se
        puede aplicar en la propia query SQL sin un join dinámico por
        tenant. La estrategia es traer todas las citas candidatas en un
        rango amplio (ej. próximas ~48h) y filtrar en Python comparando
        cada `starts_at` contra el offset específico de su cliente.
        """
        ...


    @abstractmethod
    async def mark_reminder_sent(self, appointment_id: str) -> None:
        """Marca reminder_sent_at = now() (y updated_at) tras un envío exitoso.

        Idempotente a nivel de uso: si ya estaba marcado, volver a
        marcarlo no causa un reenvío (el filtro de selección de
        candidatos exige reminder_sent_at IS NULL).
        """
        ...


class BusinessScheduleRepository(ABC):
    """Puerto de solo lectura para el horario del negocio.

    Lo implementa el repositorio de Client en infraestructura
    (el horario vive como config del tenant en la tabla clients).
    """

    @abstractmethod
    async def get_business_schedule(self, client_id: str) -> Optional[BusinessSchedule]:
        """Retorna el horario configurado del negocio, o None si el cliente no existe."""
        ...
