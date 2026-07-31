"""Tests YCloud: firma HMAC, sender y webhook inbound."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure.whatsapp.schemas import WebhookResponse
from app.infrastructure.whatsapp.sender import WhatsAppSendStatus
from app.infrastructure.whatsapp.ycloud_sender import (
    YCloudWhatsAppSender,
    categorize_ycloud_error,
    ensure_e164,
)
from app.infrastructure.whatsapp.ycloud_signature import (
    parse_ycloud_signature_header,
    verify_ycloud_signature,
)
from app.infrastructure.whatsapp.ycloud_webhook import router as ycloud_router


def _sign(secret: str, body: str, timestamp: int | None = None) -> str:
    ts = timestamp if timestamp is not None else int(time.time())
    digest = hmac.new(
        secret.encode(),
        f"{ts}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"t={ts},s={digest}"


class TestEnsureE164:
    def test_adds_plus(self) -> None:
        assert ensure_e164("34682743315") == "+34682743315"

    def test_keeps_plus(self) -> None:
        assert ensure_e164("+34682743315") == "+34682743315"


class TestYCloudSignature:
    def test_parse_header(self) -> None:
        assert parse_ycloud_signature_header("t=123,s=abc") == ("123", "abc")

    def test_verify_ok(self) -> None:
        body = '{"type":"whatsapp.inbound_message.received"}'
        header = _sign("secret", body, timestamp=1_700_000_000)
        assert verify_ycloud_signature(body, header, "secret", now=1_700_000_000) is True

    def test_verify_rejects_bad_sig(self) -> None:
        body = '{"type":"x"}'
        assert (
            verify_ycloud_signature(body, "t=1700000000,s=deadbeef", "secret", now=1_700_000_000)
            is False
        )

    def test_verify_rejects_stale(self) -> None:
        body = "{}"
        header = _sign("secret", body, timestamp=1_000)
        assert verify_ycloud_signature(body, header, "secret", now=1_700_000_000) is False


class TestCategorizeYCloudError:
    def test_401(self) -> None:
        assert categorize_ycloud_error(401, {}) == WhatsAppSendStatus.TOKEN_INVALID

    def test_429(self) -> None:
        assert categorize_ycloud_error(429, {}) == WhatsAppSendStatus.RATE_LIMITED


class TestYCloudSender:
    def test_successful_send(self) -> None:
        sender = YCloudWhatsAppSender()
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        with patch("httpx.post", return_value=mock_resp) as post:
            result = sender.send("+34682743315", "KEY", "34602438307", "hola")

        assert result.ok is True
        kwargs = post.call_args.kwargs
        assert kwargs["headers"]["X-API-Key"] == "KEY"
        assert kwargs["json"]["from"] == "+34682743315"
        assert kwargs["json"]["to"] == "+34602438307"
        assert kwargs["json"]["type"] == "text"

    def test_successful_send_template(self) -> None:
        sender = YCloudWhatsAppSender()
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        with patch("httpx.post", return_value=mock_resp) as post:
            result = sender.send_template(
                "+34682743315",
                "KEY",
                "34602438307",
                template_name="cita_recordatorio",
                language_code="es",
                body_parameters=["Orinoco Studios", "jueves 10:00"],
            )

        assert result.ok is True
        payload = post.call_args.kwargs["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "cita_recordatorio"
        assert payload["template"]["language"]["code"] == "es"
        assert payload["template"]["components"][0]["parameters"][0]["text"] == (
            "Orinoco Studios"
        )


@pytest.fixture
def ycloud_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ycloud_router)

    client_repo = AsyncMock()
    agent_repo = AsyncMock()

    from app.infrastructure.whatsapp import ycloud_webhook

    app.dependency_overrides[ycloud_webhook.get_client_repo] = lambda: client_repo
    app.dependency_overrides[ycloud_webhook.get_agent_repo] = lambda: agent_repo
    app.state.client_repo = client_repo
    app.state.agent_repo = agent_repo
    return app


class TestYCloudWebhook:
    def test_ignores_other_events(self, ycloud_app: FastAPI) -> None:
        client = TestClient(ycloud_app)
        with patch(
            "app.infrastructure.whatsapp.ycloud_webhook.get_settings"
        ) as gs:
            gs.return_value = MagicMock(ycloud_webhook_secret="")
            resp = client.post("/webhook/ycloud", json={"type": "whatsapp.message.updated"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_queues_inbound_text(self, ycloud_app: FastAPI) -> None:
        client = TestClient(ycloud_app)
        payload = {
            "type": "whatsapp.inbound_message.received",
            "whatsappInboundMessage": {
                "from": "+34602438307",
                "to": "+34682743315",
                "type": "text",
                "text": {"body": "Hola prueba"},
                "customerProfile": {"name": "Walter"},
            },
        }
        with (
            patch("app.infrastructure.whatsapp.ycloud_webhook.get_settings") as gs,
            patch(
                "app.infrastructure.whatsapp.ycloud_webhook.process_whatsapp_message",
                new_callable=AsyncMock,
                return_value=WebhookResponse(status="queued"),
            ) as proc,
        ):
            gs.return_value = MagicMock(ycloud_webhook_secret="")
            resp = client.post("/webhook/ycloud", json=payload)

        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"
        proc.assert_awaited_once()
        kwargs = proc.await_args.kwargs
        assert kwargs["phone"] == "+34602438307"
        assert kwargs["phone_number_id"] == "+34682743315"
        assert kwargs["text"] == "Hola prueba"
        assert kwargs["push_name"] == "Walter"

    def test_normalizes_to_without_plus(self, ycloud_app: FastAPI) -> None:
        client = TestClient(ycloud_app)
        payload = {
            "type": "whatsapp.inbound_message.received",
            "whatsappInboundMessage": {
                "from": "34602438307",
                "to": "34682743315",
                "type": "text",
                "text": {"body": "Hola"},
            },
        }
        with (
            patch("app.infrastructure.whatsapp.ycloud_webhook.get_settings") as gs,
            patch(
                "app.infrastructure.whatsapp.ycloud_webhook.process_whatsapp_message",
                new_callable=AsyncMock,
                return_value=WebhookResponse(status="queued"),
            ) as proc,
        ):
            gs.return_value = MagicMock(ycloud_webhook_secret="")
            resp = client.post("/webhook/ycloud", json=payload)

        assert resp.status_code == 200
        kwargs = proc.await_args.kwargs
        assert kwargs["phone"] == "+34602438307"
        assert kwargs["phone_number_id"] == "+34682743315"

    def test_rejects_bad_signature_when_secret_set(self, ycloud_app: FastAPI) -> None:
        client = TestClient(ycloud_app)
        body = {"type": "whatsapp.inbound_message.received"}
        with patch(
            "app.infrastructure.whatsapp.ycloud_webhook.get_settings"
        ) as gs:
            gs.return_value = MagicMock(ycloud_webhook_secret="super-secret")
            resp = client.post(
                "/webhook/ycloud",
                data=json.dumps(body),
                headers={
                    "Content-Type": "application/json",
                    "YCloud-Signature": "t=1,s=bad",
                },
            )
        assert resp.status_code == 401
