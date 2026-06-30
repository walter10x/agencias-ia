"""Caso de uso: desactivar un cliente (soft delete)."""

from __future__ import annotations

from app.application.dtos import ClientOutput, DeactivateClientInput, client_to_output
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import ClientNotFoundError
from app.domain.shared.value_objects import ClientId


class DeactivateClientUseCase:
    """Orquesta la desactivación (soft delete) de un cliente."""

    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, input: DeactivateClientInput) -> ClientOutput:
        client_id = ClientId.from_string(input.client_id)
        client = await self._repo.find_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(f"Client not found: {client_id}")

        client.deactivate()
        await self._repo.save(client)
        return client_to_output(client)
