"""Orchestration logic for incoming WhatsApp messages (Meta Cloud API)."""

from __future__ import annotations

from app.domain.agent.repository import AgentRepository
from app.domain.client.repository import ClientRepository
from app.domain.shared.value_objects import WhatsAppNumber
from app.infrastructure.config.celery_app import celery_app
from app.infrastructure.whatsapp.schemas import WebhookResponse

MAX_MESSAGE_LENGTH = 4096


def sanitize_message(content: str) -> str:
    """Sanitize user input before passing to LLM."""
    if not content:
        return ""

    content = content.replace("\x00", "")
    content = "".join(c for c in content if c >= " " or c in ("\n", "\t"))
    content = content.strip()
    if len(content) > MAX_MESSAGE_LENGTH:
        content = content[:MAX_MESSAGE_LENGTH]
    return content


async def process_whatsapp_message(
    phone: str,
    text: str,
    push_name: str = "",
    client_repo: ClientRepository = None,
    agent_repo: AgentRepository = None,
    phone_number_id: str = "",
) -> WebhookResponse:
    """Resuelve el tenant por `phone_number_id` (Meta) y encola el mensaje.

    Args:
        phone: número del cliente final que envía el mensaje.
        text: contenido del mensaje.
        push_name: nombre visible del contacto en WhatsApp.
        phone_number_id: identificador del número receptor de Meta. Es la
            clave de routing multi-tenant (Fase 3.3): cada tenant lo
            configura al conectar su WhatsApp. Meta lo incluye en cada
            `value.metadata`, por lo que siempre viene en mensajes reales.
    """
    if not text or not text.strip():
        return WebhookResponse(status="ignored", reason="empty_message")

    try:
        WhatsAppNumber(phone)
    except ValueError:
        return WebhookResponse(status="ignored", reason="invalid_phone")

    if not phone_number_id:
        return WebhookResponse(status="ignored", reason="missing_phone_number_id")

    client = await client_repo.find_by_phone_number_id(phone_number_id)
    if client is None:
        return WebhookResponse(status="ignored", reason="no_client")
    if not client.is_active:
        return WebhookResponse(status="ignored", reason="client_inactive")

    agents = await agent_repo.find_active_by_client(client.id)
    if not agents:
        return WebhookResponse(status="ignored", reason="no_agents")

    sanitized = sanitize_message(text)
    agent_id = str(agents[0].id)

    celery_app.send_task(
        "process_whatsapp_message",
        kwargs={
            "client_id": str(client.id),
            "phone": phone,
            "message": sanitized,
            "agent_id": agent_id,
            "push_name": push_name,
        },
    )

    return WebhookResponse(status="queued")
