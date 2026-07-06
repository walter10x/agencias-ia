"""Unit tests del webhook HTTP de WhatsApp (Meta Cloud API only).

Cubre la superficie HTTP del router:
- GET /webhook/whatsapp — verificación de suscripción de Meta.
- POST /webhook/whatsapp — recepción de mensajes (payload de Meta),
  routing por phone_number_id, y payloads no soportados.

El routing multi-tenant a nivel de dominio está cubierto en
test_whatsapp_multitenant_routing.py; aquí se testea el borde HTTP.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber

CLIENT_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AGENT_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")
VALID_WHATSAPP = "573001234567"
PHONE_NUMBER_ID = "1234567890"
VERIFY_TOKEN = "test-verify-token"


def _make_client() -> Client:
    c = Client(
        name="Test Client",
        business_type=BusinessType("otro"),
        whatsapp_number=WhatsAppNumber(VALID_WHATSAPP),
    )
    object.__setattr__(c, "id", CLIENT_UUID)
    object.__setattr__(c, "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    object.__setattr__(c, "updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    c.phone_number_id = PHONE_NUMBER_ID
    return c


def _make_agent() -> Agent:
    return Agent(
        id=AGENT_UUID,
        client_id=ClientId(CLIENT_UUID),
        name="Test Agent",
        personality="Eres un asistente amable y profesional. Diez caracteres minimo.",
        tools=[AgentTool(name="t1", description="d1", endpoint="https://n8n.example.com/t1")],
        knowledge_base_refs=[],
        is_active=True,
    )


def _meta_text_payload(text: str = "Hola", from_: str = VALID_WHATSAPP) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": PHONE_NUMBER_ID,
                            },
                            "contacts": [{"wa_id": from_, "profile": {"name": "Ana"}}],
                            "messages": [
                                {
                                    "from": from_,
                                    "id": "wamid.abc",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }


@pytest.fixture
def client_repo_mock() -> AsyncMock:
    repo = AsyncMock(spec=ClientRepository)
    repo.find_by_phone_number_id.return_value = _make_client()
    return repo


@pytest.fixture
def agent_repo_mock() -> AsyncMock:
    repo = AsyncMock(spec=AgentRepository)
    repo.find_active_by_client.return_value = [_make_agent()]
    return repo


@pytest.fixture
def app(client_repo_mock: AsyncMock, agent_repo_mock: AsyncMock) -> FastAPI:
    from app.infrastructure.http.error_handlers import register_error_handlers
    from app.infrastructure.whatsapp.webhook import (
        get_agent_repo,
        get_client_repo,
        router as whatsapp_router,
    )

    test_app = FastAPI(title="Test WhatsApp Webhook App")
    register_error_handlers(test_app)
    test_app.include_router(whatsapp_router)
    test_app.dependency_overrides[get_client_repo] = lambda: client_repo_mock
    test_app.dependency_overrides[get_agent_repo] = lambda: agent_repo_mock
    return test_app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestWebhookVerification:
    """GET /webhook/whatsapp — verificación de suscripción de Meta."""

    def _patched_settings(self):
        return patch(
            "app.infrastructure.whatsapp.webhook.get_settings",
            return_value=SimpleNamespace(whatsapp_verify_token=VERIFY_TOKEN),
        )

    def test_valid_token_returns_200_with_challenge(self, test_client: TestClient) -> None:
        with self._patched_settings():
            response = test_client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": VERIFY_TOKEN,
                    "hub.challenge": "challenge-abc-123",
                },
            )
        assert response.status_code == 200
        assert response.text == "challenge-abc-123"

    def test_invalid_token_returns_403(self, test_client: TestClient) -> None:
        with self._patched_settings():
            response = test_client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "wrong",
                    "hub.challenge": "x",
                },
            )
        assert response.status_code == 403

    def test_wrong_mode_returns_400(self, test_client: TestClient) -> None:
        with self._patched_settings():
            response = test_client.get(
                "/webhook/whatsapp",
                params={
                    "hub.mode": "unsubscribe",
                    "hub.verify_token": VERIFY_TOKEN,
                    "hub.challenge": "x",
                },
            )
        assert response.status_code == 400

    def test_missing_challenge_returns_422(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/webhook/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN},
        )
        assert response.status_code == 422


class TestWebhookMessage:
    """POST /webhook/whatsapp — recepción de mensajes de Meta."""

    def test_text_message_is_queued(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        with patch(
            "app.infrastructure.whatsapp.message_processor.celery_app"
        ) as mock_celery:
            mock_celery.send_task.return_value = MagicMock(id="task-1")
            response = test_client.post("/webhook/whatsapp", json=_meta_text_payload())

        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        client_repo_mock.find_by_phone_number_id.assert_awaited_once_with(PHONE_NUMBER_ID)
        mock_celery.send_task.assert_called_once()

    def test_unknown_object_is_ignored(self, test_client: TestClient) -> None:
        response = test_client.post(
            "/webhook/whatsapp", json={"object": "page", "entry": []}
        )
        assert response.status_code == 200
        assert response.json()["reason"] == "unsupported_payload"

    def test_non_text_message_is_ignored(self, test_client: TestClient) -> None:
        payload = _meta_text_payload()
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["type"] = "image"
        response = test_client.post("/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        assert response.json()["reason"] == "no_text_messages"

    def test_unknown_tenant_is_ignored(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        client_repo_mock.find_by_phone_number_id.return_value = None
        response = test_client.post("/webhook/whatsapp", json=_meta_text_payload())
        assert response.status_code == 200
        assert response.json()["reason"] == "no_client"
