"""Orchestration logic for incoming WhatsApp messages."""

from __future__ import annotations

import re

from app.domain.agent.repository import AgentRepository
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import InvalidMessageError
from app.domain.shared.value_objects import ClientId, WhatsAppNumber
from app.infrastructure.config.celery_app import celery_app
from app.infrastructure.whatsapp.schemas import EvolutionWebhookPayload, WebhookResponse

MAX_MESSAGE_LENGTH = 4096


def extract_phone_number(remote_jid: str) -> str:
    """Extract clean phone number from Evolution JID.

    Examples:
        "573001234567@s.whatsapp.net" → "573001234567"
        "123456789-573001234567@g.us" → "573001234567"
        "+57 300 123-4567@s.whatsapp.net" → "573001234567"
    """
    prefix = remote_jid.split("@")[0]
    if "-" in prefix:
        parts = prefix.split("-")
        if len(parts) >= 2 and len(parts[-1]) >= 10:
            prefix = parts[-1]
    phone = re.sub(r"\D", "", prefix)
    if len(phone) < 10:
        raise InvalidMessageError(f"Invalid phone number extracted: {phone} from JID {remote_jid}")
    return phone


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


async def process_evolution_message(
    payload: EvolutionWebhookPayload,
    client_repo: ClientRepository,
    agent_repo: AgentRepository,
) -> WebhookResponse:
    """Process an Evolution-format WhatsApp message.

    1. Validate event type (only messages.upsert is processed)
    2. Validate message has content
    3. Extract phone number from JID
    4. Look up Client by WhatsApp number
    5. Check client is active
    6. Find active Agents for the client
    7. Sanitize content
    8. Enqueue Celery task
    """
    if payload.event != "messages.upsert":
        return WebhookResponse(status="ignored", reason="unsupported_event")

    data = payload.data
    if data.message is None or data.message.message_type == "unknown":
        return WebhookResponse(status="ignored", reason="unsupported_message_type")

    content = data.message.content
    if content is None or not content.strip():
        return WebhookResponse(status="ignored", reason="empty_message")

    phone = extract_phone_number(data.key.remote_jid)
    push_name = data.push_name or ""

    return await process_whatsapp_message(
        phone=phone,
        text=content,
        push_name=push_name,
        client_repo=client_repo,
        agent_repo=agent_repo,
    )


# Backward compatibility alias
process = process_evolution_message


async def process_whatsapp_message(
    phone: str,
    text: str,
    push_name: str = "",
    client_repo: ClientRepository = None,
    agent_repo: AgentRepository = None,
) -> WebhookResponse:
    """Process WhatsApp message from any source (Meta, Evolution, etc)."""
    if not text or not text.strip():
        return WebhookResponse(status="ignored", reason="empty_message")

    try:
        wa = WhatsAppNumber(phone)
    except ValueError:
        return WebhookResponse(status="ignored", reason="invalid_phone")

    client = await client_repo.find_by_whatsapp(str(wa))
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
