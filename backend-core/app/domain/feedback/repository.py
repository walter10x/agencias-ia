"""Puerto de repositorio para Feedback (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.feedback.entity import Feedback


class FeedbackRepository(ABC):
    """Interfaz de repositorio para el agregado Feedback."""

    @abstractmethod
    async def save(self, feedback: Feedback) -> None:
        """Persiste un feedback."""
        ...

    @abstractmethod
    async def list_by_client(
        self,
        client_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Feedback]:
        """Lista feedbacks de un cliente, ordenados por created_at DESC."""
        ...

    @abstractmethod
    async def count_by_client(self, client_id: str) -> int:
        """Cuenta total de feedbacks de un cliente."""
        ...

    @abstractmethod
    async def get_stats(self, client_id: str) -> dict:
        """Retorna estadísticas de feedback para un cliente.

        Returns:
            dict con:
            - total: int
            - average_rating: float
            - rating_distribution: dict[int, int] (1..5 -> count)
        """
        ...
