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
    """Envía textos y plantillas vía ``POST /v2/whatsapp/messages/sendDirectly``."""

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
        return self._post(
            access_token=access_token,
            payload={
                "from": ensure_e164(phone_number_id),
                "to": ensure_e164(to),
                "type": "text",
                "text": {"body": text},
            },
            to_for_log=ensure_e164(to),
        )

    def send_template(
        self,
        phone_number_id: str,
        access_token: str,
        to: str,
        *,
        template_name: str,
        language_code: str = "es",
        body_parameters: list[str] | None = None,
    ) -> WhatsAppSendResult:
        """Envía un mensaje de plantilla (HSM) aprobada por Meta.

        Args:
            phone_number_id: Número **from** del negocio (E.164).
            access_token: YCloud API Key.
            to: Destinatario.
            template_name: Nombre exacto de la plantilla en YCloud/Meta.
            language_code: Código idioma (ej. ``es``, ``es_ES``).
            body_parameters: Valores para ``{{1}}``, ``{{2}}``, … del BODY.
        """
        params = [
            {"type": "text", "text": str(value)}
            for value in (body_parameters or [])
        ]
        template: dict = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if params:
            template["components"] = [
                {"type": "body", "parameters": params},
            ]
        return self._post(
            access_token=access_token,
            payload={
                "from": ensure_e164(phone_number_id),
                "to": ensure_e164(to),
                "type": "template",
                "template": template,
            },
            to_for_log=ensure_e164(to),
        )

    def _post(
        self,
        *,
        access_token: str,
        payload: dict,
        to_for_log: str,
    ) -> WhatsAppSendResult:
        import httpx

        url = f"{self._base}/v2/whatsapp/messages/sendDirectly"
        try:
            resp = httpx.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": access_token,
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            logger.error(f"[YCLOUD] Timeout enviando a {to_for_log}: {exc}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.UNKNOWN_ERROR, detail="timeout")
        except httpx.HTTPError as exc:
            logger.error(f"[YCLOUD] Error de red enviando a {to_for_log}: {exc}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.UNKNOWN_ERROR, detail=str(exc)[:200])

        if resp.is_success:
            logger.info(f"[YCLOUD] Enviado a {to_for_log} (type={payload.get('type')})")
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
