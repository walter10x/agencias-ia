"""Caso de uso: obtener un cliente por ID o WhatsApp."""

from __future__ import annotations

from app.application.dtos import ClientOutput, GetClientInput, client_to_output
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import ClientNotFoundError
from app.domain.shared.value_objects import ClientId, WhatsAppNumber


class GetClientUseCase:
    """Orquesta la búsqueda de un cliente por ID o número de WhatsApp."""

    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, input: GetClientInput) -> ClientOutput:
        if input.client_id:
            client_id = ClientId.from_string(input.client_id)
            client = await self._repo.find_by_id(client_id)
            if client is None:
                raise ClientNotFoundError(f"Client not found: {client_id}")
        else:
            whatsapp = WhatsAppNumber(input.whatsapp)
            client = await self._repo.find_by_whatsapp(str(whatsapp))
            if client is None:
                raise ClientNotFoundError(
                    f"Client not found by WhatsApp: {str(whatsapp)}"
                )

        return client_to_output(client)
