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

    @abstractmethod
    async def find_by_phone_number_id(self, phone_number_id: str) -> Optional[Client]:
        """Busca un cliente por su phone_number_id de Meta Cloud API.

        Usado para el routing multi-tenant del webhook entrante
        (Fase 3): Meta incluye `metadata.phone_number_id` en cada
        payload y ese valor identifica de forma única el tenant.
        """
        ...

    @abstractmethod
    async def save_whatsapp_credentials(
        self, client_id: str, phone_number_id: str, access_token: str
    ) -> None:
        """Persiste phone_number_id + access_token (cifrado) del tenant.

        El cifrado del token es responsabilidad del adaptador concreto
        (usa CredentialsCipherPort internamente) — el dominio nunca ve
        el token en claro ni conoce el algoritmo de cifrado.
        """
        ...
