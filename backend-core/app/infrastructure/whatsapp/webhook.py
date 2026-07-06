"""FastAPI router for WhatsApp webhook — receive messages from Meta Cloud API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.infrastructure.config.settings import get_settings
from app.infrastructure.whatsapp.message_processor import process_whatsapp_message
from app.infrastructure.whatsapp.rate_limiter import RateLimiter
from app.infrastructure.whatsapp.schemas import MetaWebhookPayload, WebhookResponse

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


async def get_rate_limiter(request: Request) -> RateLimiter:
    """FastAPI dependency: RateLimiter (overridden in tests).

    Reutiliza el cliente Redis compartido inicializado en el lifespan de
    la app (``app.state.redis_client``, ver ``app.main``) cuando está
    disponible, para no abrir una conexión nueva por request. Si la app
    no tiene ese estado (p. ej. instancias de test que no ejecutan el
    lifespan), crea un cliente ad hoc como antes.
    """
    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is None:
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
    """Verify webhook — used by Meta Cloud API during subscription.

    Meta sends:
    GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=12345

    Must return the raw challenge string on success.
    """
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="hub.mode must be 'subscribe'")

    settings = get_settings()
    if hub_verify_token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")

    return Response(content=hub_challenge, media_type="text/plain")


@router.post("/webhook/whatsapp")
async def receive_message(
    request: Request,
    client_repo=Depends(get_client_repo),
    agent_repo=Depends(get_agent_repo),
) -> WebhookResponse:
    """Receive WhatsApp message from Meta Cloud API.

    Meta payloads carry ``object == "whatsapp_business_account"`` and route
    to the tenant by ``value.metadata.phone_number_id`` (Fase 3.3).
    """
    body = await request.json()

    if body.get("object") != "whatsapp_business_account":
        return WebhookResponse(status="ignored", reason="unsupported_payload")

    payload = MetaWebhookPayload(**body)

    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            contacts = {c.wa_id: c.profile.get("name", "") for c in value.contacts}
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
