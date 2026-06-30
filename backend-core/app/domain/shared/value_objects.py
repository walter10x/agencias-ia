"""Value Objects compartidos del dominio."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4

from app.domain.shared.errors import InvalidClientError, InvalidAgentError
from app.domain.shared.slugify import slugify


@dataclass(frozen=True, slots=True)
class ClientId:
    """Identificador único de cliente multi-tenant."""

    value: UUID

    @classmethod
    def generate(cls) -> ClientId:
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, raw: str) -> ClientId:
        try:
            return cls(value=UUID(raw))
        except (ValueError, TypeError) as e:
            raise InvalidClientError(f"Invalid ClientId: {raw}") from e

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class AgentId:
    """Identificador único de agente IA."""

    value: UUID

    @classmethod
    def generate(cls) -> AgentId:
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, raw: str) -> AgentId:
        try:
            return cls(value=UUID(raw))
        except (ValueError, TypeError) as e:
            raise InvalidAgentError(f"Invalid AgentId: {raw}") from e

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class WhatsAppNumber:
    """Número de WhatsApp validado (formato internacional, sin '+' ni espacios)."""

    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.replace("+", "").replace(" ", "").replace("-", "")
        if not cleaned.isdigit() or len(cleaned) < 10:
            raise ValueError("WhatsApp number must be digits only, min 10 chars")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class BusinessType:
    """Tipo de negocio para personalización del agente."""

    value: str

    VALID_TYPES: frozenset[str] = frozenset({
        "peluqueria", "bar", "restaurante", "contador",
        "tienda", "gimnasio", "clinica", "otro",
        "inmobiliaria", "taller", "hotel", "ecommerce",
    })

    def __post_init__(self) -> None:
        if self.value.lower() not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid business type: {self.value}. "
                f"Valid: {sorted(self.VALID_TYPES)}"
            )
        object.__setattr__(self, "value", self.value.lower())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class LandingSlug:
    """Slug URL-safe para la landing page de un cliente.

    Invariantes:
    - Solo letras minúsculas, números y guiones
    - Mínimo 1 carácter, máximo 100
    - No puede empezar ni terminar con guion
    - No puede contener guiones consecutivos
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Landing slug cannot be empty")
        if len(self.value) > 100:
            raise ValueError("Landing slug cannot exceed 100 characters")
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", self.value):
            raise ValueError(
                "Landing slug must contain only lowercase letters, numbers, and single hyphens"
            )
        object.__setattr__(self, "value", self.value.strip().lower())

    @classmethod
    def from_name(cls, name: str) -> LandingSlug:
        """Genera un slug a partir del nombre del cliente."""
        return cls(value=slugify(name))

    def __str__(self) -> str:
        return self.value
