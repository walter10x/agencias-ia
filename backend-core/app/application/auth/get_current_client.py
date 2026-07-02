from __future__ import annotations

from app.application.dtos import CurrentClientOutput
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import AuthError
from app.domain.shared.value_objects import ClientId


class GetCurrentClientUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, client_id: str) -> CurrentClientOutput:
        try:
            cid = ClientId.from_string(client_id)
        except Exception as exc:
            raise AuthError("Invalid client ID") from exc

        client = await self._repo.find_by_id(cid)
        if client is None:
            raise AuthError("Client not found")

        return CurrentClientOutput(
            client_id=str(client.id),
            email=str(client.email) if client.email else "",
            name=client.name,
            role=client.role.value,
            status=client.status.value,
            whatsapp_number=str(client.whatsapp_number),
            whatsapp_connected=client.whatsapp_connected,
            plan=client.plan,
            is_active=client.is_active,
        )
