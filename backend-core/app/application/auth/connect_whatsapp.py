"""Caso de uso: conectar el número de WhatsApp Cloud API de un tenant.

Fase 3, tarea 3.1/5.1: persiste phone_number_id + access_token (cifrado)
por cliente. Requiere rol superadmin, igual que approve/reject/disconnect
(el flujo de autoservicio del panel — Fase 5 — reutilizará este mismo
use case cuando el propio cliente pueda conectarse sin pasar por un
superadmin).

Explícitamente NO se valida el token contra la API de Meta (el sandbox
de desarrollo/CI no tiene salida de red a Meta); la validación real
ocurre implícitamente en el primer envío real.
"""

from __future__ import annotations

from app.application.dtos import (
    AdminClientOutput,
    ConnectWhatsappInput,
    client_to_admin_output,
)
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import ForbiddenError, InvalidClientError
from app.domain.shared.value_objects import ClientId


class ConnectWhatsappUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._repo = client_repo

    async def execute(self, input: ConnectWhatsappInput, current_role: str) -> AdminClientOutput:
        if current_role != "superadmin":
            raise ForbiddenError("Only superadmin can connect WhatsApp")

        if not input.phone_number_id.strip():
            raise InvalidClientError("phone_number_id is required")
        if not input.access_token.strip():
            raise InvalidClientError("access_token is required")

        client = await self._repo.find_by_id(ClientId.from_string(input.client_id))
        if client is None:
            raise InvalidClientError("Client not found")

        # Actualiza el agregado de dominio (phone_number_id + flag) y,
        # por separado, persiste el token cifrado — el dominio Client no
        # conoce el token en claro ni el cifrado (solo infra lo maneja).
        client.connect_whatsapp(input.phone_number_id.strip())
        await self._repo.save(client)
        await self._repo.save_whatsapp_credentials(
            client_id=str(client.id),
            phone_number_id=input.phone_number_id.strip(),
            access_token=input.access_token.strip(),
        )

        return client_to_admin_output(client)
