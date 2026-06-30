"""Caso de uso: enviar mensaje proactivo a un lead."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.application.dtos import SendProactiveMessageInput
from app.domain.channels.message_sender_port import MessageSenderPort
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import (
    LeadNotFoundError,
    ProactiveMessageLimitError,
)


class SendProactiveMessageUseCase:
    """Envía un mensaje proactivo a un lead y actualiza su estado.

    Rate limit: máximo 100 mensajes proactivos/día por cliente.
    """

    DAILY_LIMIT = 100

    def __init__(
        self,
        lead_repo: LeadRepository,
        message_sender: MessageSenderPort,
    ) -> None:
        self._lead_repo = lead_repo
        self._sender = message_sender

    async def execute(self, input: SendProactiveMessageInput) -> None:
        try:
            UUID(input.lead_id)
        except ValueError:
            raise LeadNotFoundError(f"Invalid lead ID: {input.lead_id}")

        lead = await self._lead_repo.find_by_id(input.lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Lead not found: {input.lead_id}")

        # Verificar rate limit
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sent_today = await self._sender.count_sent_today(
            client_id=str(lead.client_id),
            since=today_start,
        )
        if sent_today >= self.DAILY_LIMIT:
            raise ProactiveMessageLimitError(
                f"Daily proactive message limit ({self.DAILY_LIMIT}) reached "
                f"for client {lead.client_id}"
            )

        # Enviar mensaje via MessageSenderPort
        await self._sender.send(
            phone=lead.phone,
            text=input.message_text,
        )

        # Actualizar lead
        lead.mark_contacted()
        await self._lead_repo.save(lead)
