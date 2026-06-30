"""Puerto de repositorio para Lead (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.lead.entity import Lead


class LeadRepository(ABC):
    """Interfaz de repositorio para el agregado Lead.

    Se implementa en infrastructure/persistence/.
    El dominio no conoce Supabase ni SQL.
    """

    @abstractmethod
    async def save(self, lead: Lead) -> None:
        """Persiste un lead (crear o actualizar).

        Si el lead ya existe (mismo id), hace upsert.
        """
        ...

    @abstractmethod
    async def find_by_id(self, lead_id: str) -> Optional[Lead]:
        """Busca un lead por ID. Retorna None si no existe."""
        ...

    @abstractmethod
    async def find_by_client_and_phone(
        self, client_id: str, phone: str
    ) -> Optional[Lead]:
        """Busca un lead por client_id + phone. Útil para dedup."""
        ...

    @abstractmethod
    async def list_by_client(
        self,
        client_id: str,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Lead]:
        """Lista leads de un cliente, filtrados opcionalmente por status.

        Ordenados por updated_at DESC.
        """
        ...

    @abstractmethod
    async def count_by_client(
        self,
        client_id: str,
        status: str | None = None,
    ) -> int:
        """Cuenta total de leads de un cliente, opcionalmente filtrado por status."""
        ...

    @abstractmethod
    async def get_stats(self, client_id: str) -> dict:
        """Retorna estadísticas de leads para un cliente.

        Returns:
            dict con:
            - total: int
            - by_status: dict[str, int] (new, contacted, interested, etc.)
            - conversion_rate: float (converted / total * 100)
            - new_today: int (creados hoy)
            - avg_score: float
        """
        ...

    @abstractmethod
    async def get_leads_new_today(self, client_id: str) -> list[Lead]:
        """Retorna leads creados hoy para un cliente."""
        ...

    @abstractmethod
    async def update_status_score(
        self, lead_id: str, status: str, score: int
    ) -> None:
        """Actualiza status y score de un lead (operación atómica)."""
        ...
