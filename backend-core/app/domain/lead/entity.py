"""Entidades del módulo de leads.

Lead: entidad raíz del pipeline de prospección.
LeadStatus: enum con los estados del pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class LeadStatus(str, Enum):
    """Estados del pipeline de leads."""

    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CONVERTED = "converted"
    ARCHIVED = "archived"

    @classmethod
    def valid_statuses(cls) -> frozenset[str]:
        return frozenset(s.value for s in cls)


@dataclass
class Lead:
    """Entidad que representa un lead en el pipeline de prospección.

    Invariantes:
    - client_id no puede ser nulo
    - phone no puede estar vacío
    - status debe ser un valor válido de LeadStatus
    - score debe estar entre 0 y 100
    """

    id: UUID = field(default_factory=uuid4)
    client_id: UUID = field(default_factory=uuid4)
    phone: str = ""
    name: str = ""
    status: LeadStatus = LeadStatus.NEW
    source: str = "whatsapp"
    score: int = 0
    notes: str = ""
    last_contacted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    VALID_SOURCES = frozenset({"whatsapp", "webchat", "telegram", "manual", "import", "landing"})

    def __post_init__(self) -> None:
        if not self.phone.strip():
            raise ValueError("Lead phone cannot be empty")
        # Convert string status to LeadStatus enum for adapter convenience
        if isinstance(self.status, str):
            try:
                self.status = LeadStatus(self.status)
            except ValueError:
                raise ValueError(
                    f"Invalid status: {self.status}. Valid: {sorted(LeadStatus.valid_statuses())}"
                )
        if self.status not in LeadStatus.valid_statuses():
            raise ValueError(
                f"Invalid status: {self.status}. Valid: {sorted(LeadStatus.valid_statuses())}"
            )
        if not (0 <= self.score <= 100):
            raise ValueError(f"Score must be between 0 and 100, got {self.score}")
        if self.source not in self.VALID_SOURCES:
            raise ValueError(
                f"Invalid source: {self.source}. Valid: {sorted(self.VALID_SOURCES)}"
            )

    def mark_contacted(self) -> None:
        """Marca el lead como contactado y actualiza timestamp."""
        self.status = LeadStatus.CONTACTED
        self.last_contacted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def mark_interested(self) -> None:
        """Marca el lead como interesado."""
        self.status = LeadStatus.INTERESTED
        self.last_contacted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def mark_not_interested(self) -> None:
        """Marca el lead como no interesado."""
        self.status = LeadStatus.NOT_INTERESTED
        self.score = 0
        self.updated_at = datetime.now(timezone.utc)

    def mark_converted(self) -> None:
        """Marca el lead como convertido (completó compra/reserva)."""
        self.status = LeadStatus.CONVERTED
        self.score = 100
        self.updated_at = datetime.now(timezone.utc)

    def archive(self) -> None:
        """Archiva el lead."""
        self.status = LeadStatus.ARCHIVED
        self.updated_at = datetime.now(timezone.utc)

    def add_score(self, points: int) -> None:
        """Incrementa el score (no puede exceder 100)."""
        self.score = min(100, self.score + points)
        self.updated_at = datetime.now(timezone.utc)

    def update_notes(self, notes: str) -> None:
        """Actualiza las notas del lead."""
        self.notes = notes
        self.updated_at = datetime.now(timezone.utc)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Lead):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
