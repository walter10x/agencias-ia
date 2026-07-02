from __future__ import annotations

from app.application.dtos import RegisterClientInput, RegisterClientOutput
from app.application.ports.password_hasher_port import PasswordHasherPort
from app.domain.client.entity import Client
from app.domain.client.enums import ClientRole, ClientStatus
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import (
    EmailAlreadyRegisteredError,
    InvalidClientError,
    WeakPasswordError,
)
from app.domain.shared.value_objects import BusinessType, Email, WhatsAppNumber


class RegisterClientUseCase:
    def __init__(self, client_repo: ClientRepository, password_hasher: PasswordHasherPort) -> None:
        self._repo = client_repo
        self._hasher = password_hasher

    async def execute(self, input: RegisterClientInput) -> RegisterClientOutput:
        if len(input.password) < 8:
            raise WeakPasswordError("Password must be at least 8 characters")

        try:
            email = Email(input.email)
        except ValueError as exc:
            raise InvalidClientError(f"Invalid email: {exc}") from exc

        existing = await self._repo.find_by_email(email)
        if existing is not None:
            raise EmailAlreadyRegisteredError("Email already registered")

        try:
            whatsapp = WhatsAppNumber(input.whatsapp_number)
        except ValueError as exc:
            raise InvalidClientError(str(exc)) from exc

        duplicate_wa = await self._repo.find_by_whatsapp(str(whatsapp))
        if duplicate_wa is not None:
            raise InvalidClientError("WhatsApp number already registered")

        password_hash = self._hasher.hash_password(input.password)

        client = Client(
            name=input.business_name.strip(),
            business_type=BusinessType("otro"),
            whatsapp_number=whatsapp,
            email=email,
            password_hash=password_hash,
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.PENDING,
        )

        await self._repo.save(client)

        return RegisterClientOutput(
            client_id=str(client.id),
            email=str(email),
            status="pending",
            message="Registration successful. Awaiting approval by administrator.",
        )
