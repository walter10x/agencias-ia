"""Caso de uso: crear un nuevo cliente."""

from __future__ import annotations

from app.application.dtos import ClientOutput, CreateClientInput, client_to_output
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import InvalidClientError
from app.domain.shared.value_objects import BusinessType, WhatsAppNumber


class CreateClientUseCase:
    """Orquesta la creación de un cliente validando reglas de negocio."""

    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, input: CreateClientInput) -> ClientOutput:
        if not input.name.strip():
            raise InvalidClientError("Client name cannot be empty")

        try:
            business_type = BusinessType(input.business_type)
        except ValueError as exc:
            raise InvalidClientError(str(exc)) from exc
        whatsapp = WhatsAppNumber(input.whatsapp_number)

        existing = await self._repo.find_by_whatsapp(str(whatsapp))
        if existing is not None:
            raise InvalidClientError("WhatsApp number already registered")

        client = Client(
            name=input.name.strip(),
            business_type=business_type,
            whatsapp_number=whatsapp,
        )

        await self._repo.save(client)
        return client_to_output(client)
