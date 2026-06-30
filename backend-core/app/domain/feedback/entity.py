"""Entidad del módulo de feedback.

Feedback: representa una calificación post-servicio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class Feedback:
    """Entidad que representa un feedback/calificación.

    Invariantes:
    - client_id no puede ser nulo
    - rating debe estar entre 1 y 5
    """

    id: UUID = field(default_factory=uuid4)
    client_id: UUID = field(default_factory=uuid4)
    lead_id: UUID | None = None
    conversation_id: UUID | None = None
    rating: int = 5
    comment: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not (1 <= self.rating <= 5):
            raise ValueError(f"Rating must be between 1 and 5, got {self.rating}")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Feedback):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
