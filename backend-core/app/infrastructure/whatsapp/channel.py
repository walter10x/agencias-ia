"""Factory del adaptador de envío WhatsApp según ``whatsapp_provider``."""

from __future__ import annotations

from typing import Protocol

from app.infrastructure.config.settings import Settings
from app.infrastructure.whatsapp.sender import WhatsAppSendResult, WhatsAppSender
from app.infrastructure.whatsapp.ycloud_sender import YCloudWhatsAppSender


class WhatsAppChannelSender(Protocol):
    def send(self, phone_number_id: str, access_token: str, to: str, text: str) -> WhatsAppSendResult:
        ...


def is_ycloud_provider(settings: Settings) -> bool:
    return (getattr(settings, "whatsapp_provider", None) or "meta").strip().lower() == "ycloud"


def build_whatsapp_sender(settings: Settings) -> WhatsAppChannelSender:
    """Devuelve el sender concreto (Meta o YCloud) según settings."""
    if is_ycloud_provider(settings):
        base = getattr(settings, "ycloud_api_base_url", None) or "https://api.ycloud.com"
        return YCloudWhatsAppSender(api_base_url=base)
    api_version = getattr(settings, "whatsapp_api_version", None) or "v22.0"
    return WhatsAppSender(api_version=api_version)


def resolve_global_channel_credentials(settings: Settings) -> tuple[str, str]:
    """Fallback global (from_id, api_token) según el provider activo.

    Returns:
        (routing_id, token) o ("", "") si faltan.
        - Meta: phone_number_id + access_token
        - YCloud: from E.164 + ycloud_api_key
    """
    if is_ycloud_provider(settings):
        from_number = (
            getattr(settings, "ycloud_from_number", None)
            or getattr(settings, "whatsapp_phone_number_id", None)
            or ""
        ).strip()
        api_key = (getattr(settings, "ycloud_api_key", None) or "").strip()
        if from_number and api_key:
            return from_number, api_key
        return "", ""

    phone_id = getattr(settings, "whatsapp_phone_number_id", None) or ""
    token = getattr(settings, "whatsapp_access_token", None) or ""
    if phone_id and token:
        return phone_id, token
    return "", ""
