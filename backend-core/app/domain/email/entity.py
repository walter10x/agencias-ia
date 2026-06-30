"""Entidades del modulo de email marketing.

EmailLog: registro de cada email enviado.
EmailStatus: enum con los estados de envio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class EmailStatus(str, Enum):
    """Estados de envio de email."""

    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    COMPLAINED = "complained"

    @classmethod
    def valid_statuses(cls) -> frozenset[str]:
        return frozenset(s.value for s in cls)


@dataclass
class EmailLog:
    """Entidad que registra un email enviado.

    Invariantes:
    - client_id no puede ser nulo
    - to_email no puede estar vacio
    - subject no puede estar vacio
    - template_slug debe ser un rubro valido
    """

    id: UUID = field(default_factory=uuid4)
    client_id: UUID = field(default_factory=uuid4)
    lead_id: UUID | None = None
    to_email: str = ""
    subject: str = ""
    body_html: str = ""
    template_slug: str = ""
    sequence_number: int = 1
    status: EmailStatus = EmailStatus.SENT
    resend_id: str = ""
    error_message: str = ""
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    VALID_TEMPLATES = frozenset({
        "restaurante", "peluqueria", "clinica", "tienda", "inmobiliaria",
        "gimnasio", "contador", "taller", "hotel", "ecommerce",
    })

    def __post_init__(self) -> None:
        if not self.to_email.strip():
            raise ValueError("EmailLog to_email cannot be empty")
        if not self.subject.strip():
            raise ValueError("EmailLog subject cannot be empty")
        if isinstance(self.status, str):
            try:
                self.status = EmailStatus(self.status)
            except ValueError:
                raise ValueError(
                    f"Invalid email status: {self.status}. Valid: {sorted(EmailStatus.valid_statuses())}"
                )
        if self.template_slug and self.template_slug not in self.VALID_TEMPLATES:
            raise ValueError(
                f"Invalid template_slug: {self.template_slug}. Valid: {sorted(self.VALID_TEMPLATES)}"
            )

    def mark_delivered(self) -> None:
        self.status = EmailStatus.DELIVERED

    def mark_opened(self) -> None:
        self.status = EmailStatus.OPENED

    def mark_clicked(self) -> None:
        self.status = EmailStatus.CLICKED

    def mark_bounced(self, error: str = "") -> None:
        self.status = EmailStatus.BOUNCED
        self.error_message = error

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EmailLog):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
