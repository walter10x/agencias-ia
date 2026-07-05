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


class BusinessScheduleRepository(ABC):
    """Puerto de solo lectura para el horario del negocio.

    Lo implementa el repositorio de Client en infraestructura
    (el horario vive como config del tenant en la tabla clients).
    """

    @abstractmethod
    async def get_business_schedule(self, client_id: str) -> Optional[BusinessSchedule]:
        """Retorna el horario configurado del negocio, o None si el cliente no existe."""
        ...
