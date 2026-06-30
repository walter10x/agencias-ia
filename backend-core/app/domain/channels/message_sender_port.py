"""Puerto para envío de mensajes (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class MessageSenderPort(ABC):
    """Interfaz para enviar mensajes salientes (proactivos o respuestas).

    Se implementa en infrastructure/channels/whatsapp_adapter.py
    """

    @abstractmethod
    async def send(self, phone: str, text: str) -> bool:
        """Envía un mensaje de texto a un número.

        Returns:
            True si se envió correctamente, False si falló.
        """
        ...

    @abstractmethod
    async def count_sent_today(
        self, client_id: str, since: datetime
    ) -> int:
        """Cuenta cuántos mensajes proactivos se han enviado hoy para un cliente."""
        ...
