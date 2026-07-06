"""Envío de mensajes de WhatsApp vía Meta Cloud API (DRIVEN ADAPTER).

`WhatsAppSender` recibe credenciales explícitas (phone_number_id,
access_token) en el momento del envío — NO lee settings globales — para
que cada tenant pueda usar su propio número/token (Fase 3, tarea 3.2/3.3).

El resultado del envío está tipado (`WhatsAppSendResult`) con una
categoría de error (`WhatsAppSendStatus`) derivada del código/mensaje de
error que devuelve Meta, para que `tasks.py` pueda loguear/alertar de
forma distinta según el tipo de fallo (token vencido vs. número
inválido vs. rate limit vs. desconocido).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class WhatsAppSendStatus(str, Enum):
    """Categoría del resultado de un intento de envío."""

    OK = "ok"
    TOKEN_INVALID = "token_invalid"
    NUMBER_INVALID = "number_invalid"
    RATE_LIMITED = "rate_limited"
    UNKNOWN_ERROR = "unknown_error"


# Mapeo de subcódigos/código de error de Meta Graph API a categorías.
# Referencia: https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes
_META_ERROR_CODE_MAP: dict[int, WhatsAppSendStatus] = {
    190: WhatsAppSendStatus.TOKEN_INVALID,  # Access token expirado/inválido
    463: WhatsAppSendStatus.TOKEN_INVALID,  # Sesión expirada
    131056: WhatsAppSendStatus.RATE_LIMITED,
    130429: WhatsAppSendStatus.RATE_LIMITED,  # Rate limit hit
    131047: WhatsAppSendStatus.NUMBER_INVALID,  # Re-engagement / fuera de ventana 24h
    131026: WhatsAppSendStatus.NUMBER_INVALID,  # Número de destino no en WhatsApp
    100: WhatsAppSendStatus.NUMBER_INVALID,  # Parámetro inválido (a menudo phone_number_id/to)
}


@dataclass(frozen=True, slots=True)
class WhatsAppSendResult:
    """Resultado tipado de un intento de envío."""

    status: WhatsAppSendStatus
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WhatsAppSendStatus.OK

    def to_legacy_status(self) -> str:
        """Convierte a los strings legacy usados por tasks.py/conversation.

        Se conserva "sent"/"failed" para no romper el estado persistido
        de Message.status (Fase 1). La categoría detallada solo se usa
        para logging/alertas, no se propaga al dominio de Conversation.
        """
        return "sent" if self.ok else "failed"


def categorize_meta_error(status_code: int, response_body: dict | str) -> WhatsAppSendStatus:
    """Deriva una categoría de error a partir de la respuesta de Meta.

    Args:
        status_code: Código HTTP de la respuesta.
        response_body: Body de la respuesta (dict parseado o string crudo).
    """
    error_code: int | None = None
    if isinstance(response_body, dict):
        error = response_body.get("error") or {}
        if isinstance(error, dict):
            error_code = error.get("code")

    if error_code in _META_ERROR_CODE_MAP:
        return _META_ERROR_CODE_MAP[error_code]

    if status_code == 401:
        return WhatsAppSendStatus.TOKEN_INVALID
    if status_code == 429:
        return WhatsAppSendStatus.RATE_LIMITED
    if status_code == 400:
        return WhatsAppSendStatus.NUMBER_INVALID

    return WhatsAppSendStatus.UNKNOWN_ERROR


class WhatsAppSender:
    """Envía mensajes de texto vía Meta WhatsApp Cloud API.

    Instancia sin estado de red persistente: cada llamada a `send()`
    hace su propia petición HTTP con httpx (síncrono, para uso desde
    tareas Celery que no corren en un event loop propio).
    """

    def __init__(self, api_version: str = "v22.0", timeout_seconds: float = 10.0) -> None:
        self._api_version = api_version
        self._timeout = timeout_seconds

    def send(self, phone_number_id: str, access_token: str, to: str, text: str) -> WhatsAppSendResult:
        """Envía un mensaje de texto plano.

        Args:
            phone_number_id: ID del número de WhatsApp Business (Meta) del tenant.
            access_token: Access token de Meta Cloud API del tenant, en claro
                (ya descifrado por el llamador).
            to: Número de teléfono del destinatario.
            text: Cuerpo del mensaje.

        Returns:
            WhatsAppSendResult con status OK o una categoría de error.
        """
        import httpx

        url = f"https://graph.facebook.com/{self._api_version}/{phone_number_id}/messages"
        try:
            resp = httpx.post(
                url,
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "text": {"body": text},
                },
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            logger.error(f"[WHATSAPP] Timeout enviando a {to}: {exc}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.UNKNOWN_ERROR, detail="timeout")
        except httpx.HTTPError as exc:
            logger.error(f"[WHATSAPP] Error de red enviando a {to}: {exc}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.UNKNOWN_ERROR, detail=str(exc)[:200])

        if resp.is_success:
            logger.info(f"[WHATSAPP] Enviado a {to}")
            return WhatsAppSendResult(status=WhatsAppSendStatus.OK)

        body: dict | str
        try:
            body = resp.json()
        except ValueError:
            body = resp.text

        category = categorize_meta_error(resp.status_code, body)
        logger.error(
            f"[WHATSAPP] Envío falló (status_http={resp.status_code}, "
            f"categoria={category.value}): {body}"
        )
        return WhatsAppSendResult(status=category, detail=str(body)[:300])
