"""Caso de uso: actualizar datos de un cliente."""

from __future__ import annotations

from app.application.dtos import ClientOutput, UpdateClientInput, client_to_output
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import ClientNotFoundError, InvalidClientError
from app.domain.shared.value_objects import ClientId, WhatsAppNumber


class UpdateClientUseCase:
    """Orquesta la actualización parcial de un cliente."""

    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, input: UpdateClientInput) -> ClientOutput:
        client_id = ClientId.from_string(input.client_id)
        client = await self._repo.find_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(f"Client not found: {client_id}")

        if input.name is not None:
            try:
                client.update_name(input.name)
            except ValueError as exc:
                raise InvalidClientError(str(exc)) from exc

        if input.whatsapp_number is not None:
            whatsapp = WhatsAppNumber(input.whatsapp_number)
            existing = await self._repo.find_by_whatsapp(str(whatsapp))
            if existing is not None and existing.id != client.id:
                raise InvalidClientError("WhatsApp number already registered")
            client.change_whatsapp(whatsapp)

        await self._repo.save(client)
        return client_to_output(client)
