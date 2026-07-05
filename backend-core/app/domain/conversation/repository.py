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
    async def find_by_client_and_phone(
        self, client_id: str, phone: str
    ) -> Optional[Conversation]:
        """Busca la conversación más reciente de (client_id, wa_phone_number).

        Retorna None si el cliente nunca ha conversado con ese teléfono.
        """
        ...

    @abstractmethod
    async def save(self, conversation: Conversation) -> None:
        """Crea o actualiza (upsert) una conversación."""
        ...

    @abstractmethod
    async def append_message(self, message: Message) -> None:
        """Persiste un mensaje individual dentro de una conversación."""
        ...

    @abstractmethod
    async def get_recent_messages(
        self, conversation_id: str, limit: int = 10
    ) -> list[Message]:
        """Obtiene los últimos N mensajes en orden cronológico ASC.

        Pensado para inyectar historial en el prompt del LLM.
        """
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
