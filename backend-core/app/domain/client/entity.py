"""Agregado raíz: Client.

Cada cliente representa un negocio multi-tenant (peluquería, bar, etc).
Un cliente puede tener múltiples agentes IA configurados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.domain.client.enums import ClientRole, ClientStatus
from app.domain.shared.entity import HasTimestamps
from app.domain.shared.errors import InvalidClientError
from app.domain.shared.value_objects import (
    BusinessType,
    Email,
    PasswordHash,
    WhatsAppNumber,
)


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
    email: Email | None = None
    password_hash: PasswordHash | None = None
    role: ClientRole = field(default=ClientRole.CLIENT_ADMIN)
    status: ClientStatus = field(default=ClientStatus.PENDING)
    phone_number_id: str = ""
    whatsapp_connected: bool = False
    plan: str = "free"

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

    def approve(self) -> None:
        """Aprueba el cliente: PENDING -> APPROVED."""
        if self.status != ClientStatus.PENDING:
            raise InvalidClientError("Client already approved or not pending")
        self.status = ClientStatus.APPROVED
        self.touch()

    def reject(self) -> None:
        """Rechaza el cliente: PENDING -> INACTIVE."""
        if self.status != ClientStatus.PENDING:
            raise InvalidClientError("Client is not pending")
        self.status = ClientStatus.INACTIVE
        self.is_active = False
        self.touch()

    def connect_whatsapp(self, phone_number_id: str) -> None:
        """Vincula el phone_number_id de WhatsApp Cloud API (requiere aprobación)."""
        if self.status not in (ClientStatus.APPROVED, ClientStatus.ACTIVE):
            raise InvalidClientError("Client must be approved first")
        self.phone_number_id = phone_number_id
        self.whatsapp_connected = True
        self.touch()

    def disconnect_whatsapp(self) -> None:
        """Desvincula el phone_number_id de WhatsApp Cloud API."""
        if self.status not in (ClientStatus.APPROVED, ClientStatus.ACTIVE):
            raise InvalidClientError("Client must be approved first")
        self.whatsapp_connected = False
        self.phone_number_id = ""
        self.touch()

    def can_login(self) -> bool:
        """Indica si el cliente puede iniciar sesión (APPROVED o ACTIVE)."""
        return self.status in (ClientStatus.APPROVED, ClientStatus.ACTIVE)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Client):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
