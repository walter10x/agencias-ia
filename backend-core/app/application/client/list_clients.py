"""Caso de uso: listar clientes activos con paginación."""

from __future__ import annotations

from app.application.dtos import ClientOutput, ListClientsInput, client_to_output
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import InvalidClientError


class ListClientsUseCase:
    """Orquesta la consulta paginada de clientes activos."""

    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, input: ListClientsInput) -> list[ClientOutput]:
        if input.limit < 1:
            raise InvalidClientError("limit must be >= 1")
        if input.offset < 0:
            raise InvalidClientError("offset must be >= 0")

        clients = await self._repo.list_active(input.limit, input.offset)
        return [client_to_output(c) for c in clients]
