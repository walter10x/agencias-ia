"""FastAPI router for WhatsApp webhook — YCloud inbound events.

Mantiene Meta en ``/webhook/whatsapp``. Este endpoint es independiente:

POST /webhook/ycloud

Evento esperado: ``whatsapp.inbound_message.received``
Routing multi-tenant: ``whatsappInboundMessage.to`` (E.164 del negocio)
se usa como ``phone_number_id`` en ``clients`` (misma columna que Meta).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.infrastructure.config.settings import get_settings
from app.infrastructure.whatsapp.message_processor import process_whatsapp_message
from app.infrastructure.whatsapp.schemas import WebhookResponse
from app.infrastructure.whatsapp.webhook import get_agent_repo, get_client_repo
from app.infrastructure.whatsapp.ycloud_signature import verify_ycloud_signature

logger = logging.getLogger(__name__)

router = APIRouter()

INBOUND_EVENT = "whatsapp.inbound_message.received"


@router.post("/webhook/ycloud")
async def receive_ycloud_message(
    request: Request,
    client_repo=Depends(get_client_repo),
    agent_repo=Depends(get_agent_repo),
) -> WebhookResponse:
    """Recibe mensajes entrantes desde YCloud y encola el pipeline IA."""
    raw = await request.body()
    settings = get_settings()

    secret = (settings.ycloud_webhook_secret or "").strip()
    if secret:
        signature = request.headers.get("YCloud-Signature", "")
        if not verify_ycloud_signature(raw, signature, secret):
            raise HTTPException(status_code=401, detail="Invalid YCloud signature")
    else:
        logger.warning(
            "[YCLOUD] ycloud_webhook_secret vacío — webhook sin verificación HMAC "
            "(solo aceptable en desarrollo local)."
        )

    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON body") from None

    if not isinstance(body, dict):
        return WebhookResponse(status="ignored", reason="unsupported_payload")

    event_type = body.get("type") or body.get("event")
    if event_type != INBOUND_EVENT:
        logger.info(
            "[YCLOUD] ignored event=%s keys=%s",
            event_type,
            list(body.keys())[:12],
        )
        return WebhookResponse(status="ignored", reason="unsupported_event")

    inbound = body.get("whatsappInboundMessage") or {}
    if not isinstance(inbound, dict):
        logger.info("[YCLOUD] ignored missing whatsappInboundMessage")
        return WebhookResponse(status="ignored", reason="missing_inbound_message")

    msg_type = (inbound.get("type") or "").lower()
    if msg_type and msg_type != "text":
        logger.info(
            "[YCLOUD] ignored non_text type=%s from=%s to=%s",
            msg_type,
            inbound.get("from"),
            inbound.get("to"),
        )
        return WebhookResponse(status="ignored", reason="non_text_message")

    text_obj = inbound.get("text") or {}
    text = ""
    if isinstance(text_obj, dict):
        text = (text_obj.get("body") or "").strip()
    elif isinstance(text_obj, str):
        text = text_obj.strip()

    if not text:
        logger.info(
            "[YCLOUD] ignored empty_message type=%s from=%s to=%s",
            msg_type or inbound.get("type"),
            inbound.get("from"),
            inbound.get("to"),
        )
        return WebhookResponse(status="ignored", reason="empty_message")

    from app.domain.shared.phone import normalize_phone

    from_phone = normalize_phone(str(inbound.get("from") or "")) or str(
        inbound.get("from") or ""
    ).strip()
    # Routing: YCloud manda `to` a menudo sin '+'; normalizamos a E.164.
    to_number = normalize_phone(str(inbound.get("to") or "")) or str(
        inbound.get("to") or ""
    ).strip()
    if not from_phone or not to_number:
        logger.info(
            "[YCLOUD] ignored missing_from_or_to from=%r to=%r",
            inbound.get("from"),
            inbound.get("to"),
        )
        return WebhookResponse(status="ignored", reason="missing_from_or_to")

    profile = inbound.get("customerProfile") or {}
    push_name = ""
    if isinstance(profile, dict):
        push_name = str(profile.get("name") or "").strip()

    logger.info(
        "[YCLOUD] inbound queued candidate from=%s to=%s text_len=%s",
        from_phone,
        to_number,
        len(text),
    )

    # Clave de routing: número E.164 del negocio (to). Debe coincidir con
    # clients.phone_number_id del tenant Orinoco / cliente.
    result = await process_whatsapp_message(
        phone=from_phone,
        text=text,
        push_name=push_name,
        client_repo=client_repo,
        agent_repo=agent_repo,
        phone_number_id=to_number,
    )
    logger.info(
        "[YCLOUD] process status=%s reason=%s from=%s",
        result.status,
        result.reason,
        from_phone,
    )
    return result
