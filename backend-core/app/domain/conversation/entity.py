"""Entidades del módulo de conversaciones.

Conversation: agregado raíz del chat.
Message: entidad dentro de una conversación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ConversationStatus(str, Enum):
    """Estados posibles de una conversación según la BD."""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


@dataclass
class Message:
    """Mensaje individual dentro de una conversación.

    Invariantes:
    - role debe ser 'user', 'assistant', o 'system'
    - content no puede estar vacío
    - conversation_id debe ser válido
    - status debe ser 'received', 'sent', 'failed', o 'skipped'

    Semántica de status:
    - received: mensaje entrante del usuario final.
    - sent: respuesta del agente confirmada por Meta Cloud API.
    - failed: el envío a Meta falló.
    - skipped: Meta no está configurado; el mensaje NO se envió (solo logs).
    """

    VALID_STATUSES = frozenset({"received", "sent", "failed", "skipped"})

    id: UUID = field(default_factory=uuid4)
    conversation_id: UUID = field(default_factory=uuid4)
    role: str = ""
    content: str = ""
    tokens_used: int = 0
    status: str = "received"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        valid_roles = {"user", "assistant", "system"}
        if self.role not in valid_roles:
            raise ValueError(f"Invalid role: {self.role}. Must be one of {valid_roles}")
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {self.status}. Valid: {sorted(self.VALID_STATUSES)}"
            )


@dataclass
class Conversation:
    """Agregado raíz que representa un hilo de conversación WhatsApp.

    Invariantes:
    - client_id no puede ser nulo
    - wa_phone_number no puede estar vacío
    - status debe ser 'active', 'closed', o 'archived'
    """

    id: UUID = field(default_factory=uuid4)
    client_id: UUID = field(default_factory=uuid4)
    agent_id: UUID | None = None
    wa_phone_number: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Cache del último mensaje (NO persistido — llenado por repositorio)
    last_message: str | None = None

    VALID_STATUSES = frozenset({"active", "closed", "archived"})

    def __post_init__(self) -> None:
        if not self.wa_phone_number.strip():
            raise ValueError("Phone number cannot be empty")
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {self.status}. Valid: {sorted(self.VALID_STATUSES)}"
            )

    def close(self) -> None:
        """Cierra la conversación."""
        self.status = "closed"
        self.updated_at = datetime.now(timezone.utc)

    def archive(self) -> None:
        """Archiva la conversación."""
        self.status = "archived"
        self.updated_at = datetime.now(timezone.utc)

    def reopen(self) -> None:
        """Reabre una conversación cerrada/archivada."""
        self.status = "active"
        self.updated_at = datetime.now(timezone.utc)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Conversation):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
