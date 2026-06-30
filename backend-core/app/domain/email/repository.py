"""Puerto de repositorio para EmailLog (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.email.entity import EmailLog


class EmailRepository(ABC):
    """Interfaz de repositorio para el agregado EmailLog."""

    @abstractmethod
    async def save(self, log: EmailLog) -> None:
        """Persiste un registro de email (crear)."""
        ...

    @abstractmethod
    async def find_by_id(self, log_id: str) -> Optional[EmailLog]:
        """Busca un email log por ID."""
        ...

    @abstractmethod
    async def list_by_client(
        self,
        client_id: str,
        lead_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[EmailLog]:
        """Lista emails de un cliente, opcionalmente filtrados por lead."""
        ...

    @abstractmethod
    async def count_by_client(self, client_id: str) -> int:
        """Cuenta total de emails enviados por cliente."""
        ...

    @abstractmethod
    async def get_stats(self, client_id: str) -> dict:
        """Retorna estadisticas de email marketing para un cliente.

        Returns:
            dict con:
            - total_sent: int
            - total_opened: int
            - total_clicked: int
            - total_bounced: int
            - open_rate: float
            - click_rate: float
            - by_template: dict[str, int]
        """
        ...
