"""Envío de mensajes de WhatsApp vía YCloud API (DRIVEN ADAPTER).

Misma firma que ``WhatsAppSender`` (Meta): ``phone_number_id`` se interpreta
como el número **from** en E.164 del negocio, y ``access_token`` como la
API Key de YCloud (``X-API-Key``). Así Celery / notifiers no cambian de
contrato al cambiar ``whatsapp_provider``.
"""

from __future__ import annotations

import logging

from app.infrastructure.whatsapp.sender import WhatsAppSendResult, WhatsAppSendStatus

logger = logging.getLogger(__name__)


def ensure_e164(number: str) -> str:
    """Normaliza a E.164 con prefijo '+' (YCloud lo exige)."""
    cleaned = (number or "").replace(" ", "").replace("-", "")
    if not cleaned:
        return cleaned
    if cleaned.startswith("+"):
        return cleaned
    return f"+{cleaned}"


def categorize_ycloud_error(status_code: int, response_body: dict | str) -> WhatsAppSendStatus:
    """Mapea errores HTTP / body de YCloud a las mismas categorías que Meta."""
    if status_code == 401 or status_code == 403:
        return WhatsAppSendStatus.TOKEN_INVALID
    if status_code == 429:
        return WhatsAppSendStatus.RATE_LIMITED
    if status_code == 400:
        return WhatsAppSendStatus.NUMBER_INVALID

    if isinstance(response_body, dict):
        code = str(response_body.get("code") or response_body.get("errorCode") or "").lower()
        msg = str(response_body.get("message") or response_body.get("error") or "").lower()
        blob = f"{code} {msg}"
        if "unauthor" in blob or "api key" in blob or "forbidden" in blob:
            return WhatsAppSendStatus.TOKEN_INVALID
        if "rate" in blob or "throttl" in blob:
            return WhatsAppSendStatus.RATE_LIMITED
        if "invalid" in blob or "recipient" in blob or "phone" in blob:
            return WhatsAppSendStatus.NUMBER_INVALID

    return WhatsAppSendStatus.UNKNOWN_ERROR


class YCloudWhatsAppSender:
    """Envía textos vía ``POST /v2/whatsapp/messages/sendDirectly``."""

    def __init__(
        self,
        api_base_url: str = "https://api.ycloud.com",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base = api_base_url.rstrip("/")
        self._timeout = timeout_seconds

    def send(self, phone_number_id: str, access_token: str, to: str, text: str) -> WhatsAppSendResult:
        """Envía un mensaje de texto.

        Args:
            phone_number_id: Número **from** del negocio (E.164).
            access_token: YCloud API Key.
            to: Destinatario (E.164 o dígitos).
            text: Cuerpo del mensaje.
        """
        import httpx

        from_number = ensure_e164(phone_number_id)
        to_number = ensure_e164(to)
        url = f"{self._base}/v2/whatsapp/messages/sendDirectly"

        try:
            resp = httpx.post(
                url,
                json={
                    "from": from_number,
                    "to": to_number,
                    "type": "text",
                    "text": {"body": text},
                },
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": access_token,
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            logger.error(f"[YCLOUD] Timeout enviando a {to_number}: {exc}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.UNKNOWN_ERROR, detail="timeout")
        except httpx.HTTPError as exc:
            logger.error(f"[YCLOUD] Error de red enviando a {to_number}: {exc}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.UNKNOWN_ERROR, detail=str(exc)[:200])

        if resp.is_success:
            logger.info(f"[YCLOUD] Enviado a {to_number}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.OK)

        body: dict | str
        try:
            body = resp.json()
        except ValueError:
            body = resp.text

        category = categorize_ycloud_error(resp.status_code, body)
        logger.error(
            f"[YCLOUD] Envío falló (status_http={resp.status_code}, "
            f"categoria={category.value}): {body}"
        )
        return WhatsAppSendResult(status=category, detail=str(body)[:300])
