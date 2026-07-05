"""FastAPI router for WhatsApp webhook — receive messages from Meta Cloud API + Evolution API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

from app.infrastructure.config.settings import get_settings
from app.infrastructure.whatsapp.message_processor import (
    extract_phone_number,
    process_whatsapp_message,
)
from app.infrastructure.whatsapp.rate_limiter import RateLimiter
from app.infrastructure.whatsapp.schemas import (
    EvolutionWebhookPayload,
    MetaWebhookPayload,
    WebhookResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_client_repo():
    """FastAPI dependency: ClientRepository (overridden in tests)."""
    from app.infrastructure.persistence.client_repository import SupabaseClientRepository
    from app.infrastructure.http.supabase_client import SupabaseHttpClient

    settings = get_settings()
    client = SupabaseHttpClient(settings.supabase_url, settings.supabase_service_key)
    return SupabaseClientRepository(client)


def get_agent_repo():
    """FastAPI dependency: AgentRepository (overridden in tests)."""
    from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository
    from app.infrastructure.http.supabase_client import SupabaseHttpClient

    settings = get_settings()
    client = SupabaseHttpClient(settings.supabase_url, settings.supabase_service_key)
    return SupabaseAgentRepository(client)


async def get_rate_limiter() -> RateLimiter:
    """FastAPI dependency: RateLimiter (overridden in tests)."""
    import redis.asyncio as async_redis

    settings = get_settings()
    redis_client = async_redis.from_url(settings.redis_url)
    return RateLimiter(redis_client)


@router.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> Response:
    """Verify webhook — used by both Meta Cloud API and Evolution API.

    Meta/Evo sends:
    GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=12345

    Must return the raw challenge string on success.
    """
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="hub.mode must be 'subscribe'")

    settings = get_settings()
    valid_token = settings.whatsapp_verify_token or settings.evolution_api_key
    if hub_verify_token != valid_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")

    return Response(content=hub_challenge, media_type="text/plain")


@router.post("/webhook/whatsapp")
async def receive_message(
    request: Request,
    client_repo=Depends(get_client_repo),
    agent_repo=Depends(get_agent_repo),
):
    """Receive WhatsApp message from Meta Cloud API OR Evolution API.

    Detects format automatically:
    - Meta: body.object == "whatsapp_business_account"
    - Evolution: has "event" field
    """
    body = await request.json()

    # Detect Meta format
    if body.get("object") == "whatsapp_business_account":
        return await _handle_meta_message(body, client_repo, agent_repo)

    # Fallback: Evolution format
    payload = EvolutionWebhookPayload(**body)
    if payload.event not in ("messages.upsert", "messages.update"):
        return WebhookResponse(status="ignored", reason="unsupported_event")

    if payload.data.key.from_me:
        return WebhookResponse(status="ignored", reason="from_me")

    phone = payload.data.key.extract_phone()
    content = payload.data.message.content if payload.data.message else ""
    push_name = payload.data.push_name or ""

    return await process_whatsapp_message(
        phone=phone,
        text=content or "",
        push_name=push_name or "",
        client_repo=client_repo,
        agent_repo=agent_repo,
    )


async def _handle_meta_message(
    body: dict,
    client_repo,
    agent_repo,
) -> WebhookResponse:
    """Process Meta WhatsApp Cloud API message."""
    payload = MetaWebhookPayload(**body)

    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            contacts = {c.wa_id: c.profile.get("name", "") for c in value.contacts}
            # Routing multi-tenant (Fase 3.3): Meta identifica el número
            # receptor (y por tanto el tenant) en value.metadata.phone_number_id.
            phone_number_id = value.metadata.phone_number_id

            for msg in value.messages:
                if msg.type != "text":
                    continue

                phone = msg.from_
                text = msg.text.body
                push_name = contacts.get(phone, "")

                if text:
                    return await process_whatsapp_message(
                        phone=phone,
                        text=text,
                        push_name=push_name,
                        client_repo=client_repo,
                        agent_repo=agent_repo,
                        phone_number_id=phone_number_id,
                    )

    return WebhookResponse(status="ignored", reason="no_text_messages")