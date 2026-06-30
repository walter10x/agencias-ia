"""Entidad base para todos los agregados del dominio."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID


class HasTimestamps:
    """Mixin que añade timestamps de creación/actualización."""

    created_at: datetime
    updated_at: datetime

    def _init_timestamps(self) -> None:
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now

    def touch(self) -> None:
        """Actualiza el timestamp de modificación."""
        self.updated_at = datetime.now(timezone.utc)
