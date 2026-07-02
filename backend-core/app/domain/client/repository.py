"""Puerto de repositorio para Client (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.client.entity import Client
from app.domain.shared.value_objects import ClientId, Email


class ClientRepository(ABC):
    """Interfaz de repositorio para el agregado Client.

    Se implementa en infrastructure/persistence/.
    El dominio no conoce Supabase ni SQL.
    """

    @abstractmethod
    async def save(self, client: Client) -> None:
        """Guarda o actualiza un cliente."""
        ...

    @abstractmethod
    async def find_by_id(self, client_id: ClientId) -> Optional[Client]:
        """Busca un cliente por su ID."""
        ...

    @abstractmethod
    async def find_by_whatsapp(self, number: str) -> Optional[Client]:
        """Busca un cliente por su número de WhatsApp."""
        ...

    @abstractmethod
    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Client]:
        """Lista clientes activos con paginación."""
        ...

    @abstractmethod
    async def find_by_email(self, email: Email) -> Optional[Client]:
        """Busca un cliente por su email (para login y pre-check de duplicado)."""
        ...
