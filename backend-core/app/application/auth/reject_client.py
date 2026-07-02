from __future__ import annotations

from app.application.dtos import AdminClientOutput, RejectClientInput, client_to_admin_output
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import ForbiddenError, InvalidClientError
from app.domain.shared.value_objects import ClientId


class RejectClientUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, input: RejectClientInput, current_role: str) -> AdminClientOutput:
        if current_role != "superadmin":
            raise ForbiddenError("Only superadmin can reject clients")

        client = await self._repo.find_by_id(ClientId.from_string(input.client_id))
        if client is None:
            raise InvalidClientError("Client not found")

        client.reject()
        await self._repo.save(client)
        return client_to_admin_output(client)
