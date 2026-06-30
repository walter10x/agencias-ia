"""Agregado raíz: Client.

Cada cliente representa un negocio multi-tenant (peluquería, bar, etc).
Un cliente puede tener múltiples agentes IA configurados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.domain.shared.entity import HasTimestamps
from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber


@dataclass
class Client(HasTimestamps):
    """Agregado raíz que representa un negocio cliente de la plataforma.

    Invariantes:
    - name no puede estar vacío
    - whatsapp_number debe ser válido
    - business_type debe ser uno de los tipos permitidos
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    business_type: BusinessType = field(default_factory=lambda: BusinessType("otro"))
    whatsapp_number: WhatsAppNumber = field(default_factory=lambda: WhatsAppNumber("0000000000"))
    is_active: bool = True

    def __post_init__(self) -> None:
        self._init_timestamps()
        if not self.name.strip():
            raise ValueError("Client name cannot be empty")

    def deactivate(self) -> None:
        """Desactiva el cliente (soft delete)."""
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        """Reactiva el cliente."""
        self.is_active = True
        self.touch()

    def update_name(self, new_name: str) -> None:
        """Actualiza el nombre del negocio."""
        if not new_name.strip():
            raise ValueError("Client name cannot be empty")
        self.name = new_name.strip()
        self.touch()

    def change_whatsapp(self, new_number: WhatsAppNumber) -> None:
        """Cambia el número de WhatsApp asociado."""
        self.whatsapp_number = new_number
        self.touch()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Client):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
