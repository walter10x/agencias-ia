"""Puerto de repositorio para Landing (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.client.entity import Client


@dataclass
class LandingConfig:
    """Value object con la configuración de landing de un cliente."""
    client_id: str
    slug: str
    title: str
    description: str
    is_active: bool
    primary_color: str
    auto_reply: str


class LandingRepository(ABC):
    """Interfaz para operaciones de landing page."""

    @abstractmethod
    async def find_client_by_slug(self, slug: str) -> tuple[Client, LandingConfig] | None:
        """Busca cliente + config por slug. Retorna None si no existe."""
        ...

    @abstractmethod
    async def get_landing_config(self, client_id: str) -> LandingConfig | None:
        """Obtiene config de landing de un cliente."""
        ...

    @abstractmethod
    async def update_landing_config(self, client_id: str, data) -> LandingConfig:
        """Actualiza columnas de landing."""
        ...

    @abstractmethod
    async def slug_exists(self, slug: str, exclude_client_id: str | None = None) -> bool:
        """Verifica unicidad de slug."""
        ...

    @abstractmethod
    async def count_leads_by_landing(self, client_id: str) -> int:
        """Cuenta leads con source='landing'."""
        ...

    @abstractmethod
    async def check_rate_limit(self, ip: str, max_req: int = 5, window_sec: int = 60) -> bool:
        """Verifica rate limit por IP."""
        ...

    @abstractmethod
    async def get_all_slugs(self) -> set[str]:
        """Obtiene todos los slugs existentes."""
        ...

    @abstractmethod
    async def get_client(self, client_id: str) -> Client | None:
        """Obtiene un cliente por ID."""
        ...
