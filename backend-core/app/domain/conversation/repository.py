"""Puerto de repositorio para Conversation (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.conversation.entity import Conversation, Message


class ConversationRepository(ABC):
    """Interfaz de repositorio para el agregado Conversation.

    Se implementa en infrastructure/persistence/.
    El dominio no conoce Supabase ni SQL.
    """

    @abstractmethod
    async def list_by_client(
        self,
        client_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """Lista conversaciones de un cliente, ordenadas por updated_at DESC.

        Cada Conversation debe incluir last_message con el contenido
        del mensaje más reciente (o None si no tiene mensajes).
        """
        ...

    @abstractmethod
    async def count_by_client(self, client_id: str) -> int:
        """Cuenta total de conversaciones de un cliente."""
        ...

    @abstractmethod
    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Obtiene todos los mensajes de una conversación ordenados ASC."""
        ...

    @abstractmethod
    async def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Busca una conversación por ID. Retorna None si no existe."""
        ...

    @abstractmethod
    async def get_stats(self) -> dict:
        """Retorna estadísticas globales de conversaciones.

        Returns:
            dict con:
            - total_conversations: int
            - active_conversations: int
            - messages_today: int
            - clients_with_conversations: int
        """
        ...
