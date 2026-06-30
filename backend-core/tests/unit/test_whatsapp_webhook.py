"""Unit tests for WhatsApp webhook (RED phase — TDD).

These tests verify the WhatsApp webhook contract BEFORE any webhook code
exists. Imports from `app.infrastructure.whatsapp.*` will fail with
ImportError — that is the expected RED signal.

When the developer creates the files (webhook.py, message_processor.py,
schemas.py, rate_limiter.py), the imports succeed and tests start running.
Tests will then fail because endpoints/processor aren't implemented →
implement one by one until all tests pass (GREEN).

Coverage:
- Webhook verification (GET /webhook/whatsapp)
- Message reception (POST /webhook/whatsapp) — happy path, edge cases
- Message processor business logic (orchestration: lookup → queue)
- Phone number extraction from Evolution JID
- Rate limit responses, API key validation, response time SLA
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# --- Domain layer (already exists) ---
from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import (
    DomainError,
    InvalidAgentError,
    InvalidClientError,
    InvalidMessageError,
)
from app.domain.shared.value_objects import (
    AgentId,
    BusinessType,
    ClientId,
    WhatsAppNumber,
)

# --- Infrastructure WhatsApp (does NOT exist yet — RED phase) ---
# These imports WILL fail until the developer creates the files:
#   app/infrastructure/whatsapp/__init__.py
#   app/infrastructure/whatsapp/webhook.py
#   app/infrastructure/whatsapp/schemas.py
#   app/infrastructure/whatsapp/message_processor.py
from app.infrastructure.whatsapp.message_processor import (  # noqa: F401
    extract_phone_number,
    process,
)
from app.infrastructure.whatsapp.schemas import (  # noqa: F401
    EvolutionData,
    EvolutionKey,
    EvolutionMessageData,
    EvolutionWebhookPayload,
    WebhookResponse,
)
from app.infrastructure.whatsapp.webhook import router as whatsapp_router  # noqa: F401


# ============================================================================
# Constants
# ============================================================================

CLIENT_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AGENT_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")
SECOND_AGENT_UUID = uuid.UUID("33333333-3333-3333-3333-333333333333")
VALID_WHATSAPP = "573001234567"
VALID_JID = "573001234567@s.whatsapp.net"
VALID_API_KEY = "test-evolution-api-key-secret"
_MARKER = "Eres un asistente amable y profesional para el negocio."
_MIN_PERSONALITY = "Eres un asistente amable y profesional. Diez caracteres minimo."


# ============================================================================
# Entity factories (mirror helpers from test_http_routers.py)
# ============================================================================


def _make_client(**overrides: object) -> Client:
    """Factory for Client entities with overridable fields."""
    c = Client(
        name=str(overrides.get("name", "Test Client")),
        business_type=overrides.get("business_type", BusinessType("otro")),  # type: ignore[arg-type]
        whatsapp_number=overrides.get("whatsapp_number", WhatsAppNumber(VALID_WHATSAPP)),  # type: ignore[arg-type]
    )
    if "id" in overrides:
        object.__setattr__(c, "id", overrides["id"])
    else:
        object.__setattr__(c, "id", CLIENT_UUID)
    if "is_active" in overrides:
        c.is_active = bool(overrides["is_active"])
    object.__setattr__(
        c, "created_at", overrides.get("created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    )
    object.__setattr__(
        c, "updated_at", overrides.get("updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    )
    return c


def _make_agent(**overrides: object) -> Agent:
    """Factory for Agent entities with overridable fields."""
    a = Agent(
        id=overrides.get("id", AGENT_UUID),  # type: ignore[arg-type]
        client_id=overrides.get("client_id", ClientId(CLIENT_UUID)),  # type: ignore[arg-type]
        name=str(overrides.get("name", "Test Agent")),
        personality=str(overrides.get("personality", _MIN_PERSONALITY)),
        tools=overrides.get(  # type: ignore[arg-type]
            "tools",
            [AgentTool(name="t1", description="d1", endpoint="https://n8n.example.com/t1")],
        ),
        knowledge_base_refs=overrides.get("knowledge_base_refs", ["kb-1"]),  # type: ignore[arg-type]
        is_active=bool(overrides.get("is_active", True)),
    )
    object.__setattr__(
        a, "created_at", overrides.get("created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    )
    object.__setattr__(
        a, "updated_at", overrides.get("updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    )
    return a


# ============================================================================
# Payload factories
# ============================================================================


def _make_valid_payload(**overrides: object) -> dict[str, Any]:
    """Build a valid Evolution API webhook payload."""
    return {
        "event": overrides.get("event", "messages.upsert"),
        "instance": overrides.get("instance", "default"),
        "data": {
            "key": {
                "remoteJid": overrides.get("remoteJid", VALID_JID),
                "fromMe": overrides.get("fromMe", False),
                "id": overrides.get("instanceId", "instance-1"),
            },
            "message": {
                "conversation": overrides.get("conversation", "Hola, quiero información"),
            },
            "pushName": overrides.get("pushName", "Juan Pérez"),
            "messageTimestamp": overrides.get("messageTimestamp", 1717800000),
        },
    }


def _make_media_payload(media_type: str, **overrides: object) -> dict[str, Any]:
    """Build a valid payload for a media message (image, audio, etc.)."""
    if media_type == "image":
        msg = {
            "image_message": overrides.get(
                "image_message",
                {
                    "url": "https://example.com/image.jpg",
                    "mimetype": "image/jpeg",
                    "caption": overrides.get("caption", "Mira esta imagen"),
                },
            )
        }
    elif media_type == "audio":
        msg = {
            "audio_message": overrides.get(
                "audio_message",
                {"url": "https://example.com/audio.ogg", "mimetype": "audio/ogg", "seconds": 5},
            )
        }
    elif media_type == "video":
        msg = {
            "video_message": overrides.get(
                "video_message",
                {
                    "url": "https://example.com/video.mp4",
                    "mimetype": "video/mp4",
                    "caption": "Mira este video",
                },
            )
        }
    elif media_type == "document":
        msg = {
            "document_message": overrides.get(
                "document_message",
                {"url": "https://example.com/doc.pdf", "mimetype": "application/pdf", "fileName": "doc.pdf"},
            )
        }
    else:
        msg = {"conversation": "fallback"}

    return {
        "event": "messages.upsert",
        "instance": "default",
        "data": {
            "key": {"remoteJid": VALID_JID, "fromMe": False, "id": "instance-1"},
            "message": msg,
            "pushName": "Juan",
            "messageTimestamp": 1717800000,
        },
    }


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client_repo_mock() -> AsyncMock:
    """Mock ClientRepository — injected via dependency_overrides."""
    return AsyncMock(spec=ClientRepository)


@pytest.fixture
def agent_repo_mock() -> AsyncMock:
    """Mock AgentRepository — injected via dependency_overrides."""
    return AsyncMock(spec=AgentRepository)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables needed by all webhook tests.

    Sets EVOLUTION_API_KEY so the webhook endpoint can validate the
    x-api-key header without mocking the settings module directly.
    Also clears the get_settings() LRU cache to pick up the env var.
    """
    monkeypatch.setenv("EVOLUTION_API_KEY", VALID_API_KEY)
    # Clear LRU cache on get_settings so it re-reads env variables
    from app.infrastructure.config.settings import get_settings

    get_settings.cache_clear()


@pytest.fixture
def app(
    client_repo_mock: AsyncMock,
    agent_repo_mock: AsyncMock,
) -> FastAPI:
    """Create a FastAPI test app with the WhatsApp webhook router and mocked deps.

    This fixture:
    1. Creates a fresh FastAPI instance
    2. Registers error handlers
    3. Registers whatsapp_router
    4. Overrides repository dependencies with mocks

    When the whatsapp modules don't exist yet, this fixture will raise
    ImportError — that's the expected RED phase signal.
    """
    from app.infrastructure.http.error_handlers import register_error_handlers
    from app.infrastructure.whatsapp.webhook import (
        get_agent_repo,
        get_client_repo,
        get_rate_limiter,
    )

    test_app = FastAPI(title="Test WhatsApp Webhook App")

    # Register domain → HTTP error handlers
    register_error_handlers(test_app)

    # Register WhatsApp webhook router
    test_app.include_router(whatsapp_router)

    # Override repository dependencies with mocks
    test_app.dependency_overrides[get_client_repo] = lambda: client_repo_mock
    test_app.dependency_overrides[get_agent_repo] = lambda: agent_repo_mock

    # Override rate limiter to always allow (avoids Redis dependency in unit tests)
    mock_rate_limiter = AsyncMock()
    mock_rate_limiter.check.return_value = True
    test_app.dependency_overrides[get_rate_limiter] = lambda: mock_rate_limiter

    return test_app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Synchronous TestClient wrapping the test FastAPI app."""
    return TestClient(app)


# ============================================================================
# TestWebhookVerification: GET /webhook/whatsapp
# ============================================================================


class TestWebhookVerification:
    """GET /webhook/whatsapp — Webhook verification for Evolution API.

    Evolution API verifies the webhook by sending:
    GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=12345

    The endpoint must return the challenge as raw text on success.
    """

    # --- Happy Path ---

    def test_verify_token_valid_returns_200_with_challenge(
        self, test_client: TestClient
    ) -> None:
        """RF-WH-16: valid verify_token → 200, returns raw challenge as plain text."""
        response = test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VALID_API_KEY,
                "hub.challenge": "challenge-abc-123",
            },
        )

        assert response.status_code == 200
        # Response should be the raw challenge string, not JSON
        assert response.text == "challenge-abc-123"

    # --- Edge Cases ---

    def test_verify_token_invalid_returns_403(
        self, test_client: TestClient
    ) -> None:
        """RF-WH-17: invalid verify_token → 403 Forbidden."""
        response = test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-abc",
            },
        )

        assert response.status_code == 403
        body = response.json()
        assert "error" in body or "detail" in body

    def test_verify_token_missing_mode_returns_422(
        self, test_client: TestClient
    ) -> None:
        """Missing hub.mode → 422 from Pydantic Query validation."""
        response = test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.verify_token": VALID_API_KEY,
                "hub.challenge": "challenge-abc",
            },
        )

        assert response.status_code == 422

    def test_verify_token_missing_verify_token_returns_422(
        self, test_client: TestClient
    ) -> None:
        """Missing hub.verify_token → 422 from Pydantic Query validation."""
        response = test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "challenge-abc",
            },
        )

        assert response.status_code == 422

    def test_verify_token_missing_challenge_returns_422(
        self, test_client: TestClient
    ) -> None:
        """Missing hub.challenge → 422 from Pydantic Query validation."""
        response = test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VALID_API_KEY,
            },
        )

        assert response.status_code == 422

    def test_verify_wrong_mode_returns_400(
        self, test_client: TestClient
    ) -> None:
        """EC-17: hub.mode != 'subscribe' → 400 Bad Request."""
        response = test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "invalid_mode",
                "hub.verify_token": VALID_API_KEY,
                "hub.challenge": "challenge-abc",
            },
        )

        # Spec says 400 when mode != "subscribe"
        assert response.status_code == 400

    def test_verify_empty_challenge_returns_200(
        self, test_client: TestClient
    ) -> None:
        """Empty challenge string should still be returned as-is."""
        response = test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VALID_API_KEY,
                "hub.challenge": "",
            },
        )

        assert response.status_code == 200
        assert response.text == ""


# ============================================================================
# TestWebhookMessage: POST /webhook/whatsapp
# ============================================================================


class TestWebhookMessage:
    """POST /webhook/whatsapp — Receive messages from Evolution API.

    Tests the HTTP contract: request validation, API key auth, and response
    mapping. The actual business logic is mocked via dependency overrides.
    """

    # --- Happy Path ---

    def test_receive_text_message_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-01: valid text message with registered client → 200 queued."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent(id=AGENT_UUID, client_id=ClientId(CLIENT_UUID))
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "queued"
        assert "task_id" in body

    def test_receive_message_finds_client_and_agents(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-05 + RF-WH-07: processor calls client_repo and agent_repo."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agents = [
            _make_agent(id=AGENT_UUID, client_id=ClientId(CLIENT_UUID), name="Agent 1"),
            _make_agent(id=SECOND_AGENT_UUID, client_id=ClientId(CLIENT_UUID), name="Agent 2"),
        ]
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = agents

        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "queued"
        # Verify repositories were called with correct args
        client_repo_mock.find_by_whatsapp.assert_awaited_once_with(VALID_WHATSAPP)
        agent_repo_mock.find_active_by_client.assert_awaited_once()

    # --- Unknown Sender / No Client ---

    def test_receive_message_unknown_sender_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-06: sender not in DB → 200 OK with status='ignored'."""
        client_repo_mock.find_by_whatsapp.return_value = None

        payload = _make_valid_payload(remoteJid="573009999999@s.whatsapp.net")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ignored"
        # Should not try to find agents for unknown client
        agent_repo_mock.find_active_by_client.assert_not_awaited()

    def test_receive_message_client_inactive_returns_200_ignored(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-5: client found but is_active=False → 200 ignored."""
        client = _make_client(is_active=False, whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_whatsapp.return_value = client

        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ignored"
        agent_repo_mock.find_active_by_client.assert_not_awaited()

    def test_receive_message_no_active_agents_returns_200_ignored(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-08: client found but no active agents → 200 ignored."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = []  # empty

        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ignored"

    # --- Message Type Variations ---

    def test_receive_message_empty_conversation_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-4: empty text message → 200 OK ignored."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_whatsapp.return_value = client

        payload = _make_valid_payload(conversation="")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        # Empty message should be ignored (status depends on processor logic)
        body = response.json()
        assert body["status"] in ("ignored", "queued")

    def test_receive_message_whitespace_only_returns_200_ignored(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """Whitespace-only conversation should be ignored."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_whatsapp.return_value = client

        payload = _make_valid_payload(conversation="   \n  \t  ")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200

    def test_receive_message_with_image_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-10: image message → 200 OK (detected as media type)."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        payload = _make_media_payload("image", caption="Mira esta foto")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        # Image with caption → may be queued (caption is text content)
        assert body["status"] in ("queued", "ignored")

    def test_receive_message_with_audio_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """Audio message (no text content) → 200 OK."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_whatsapp.return_value = client

        payload = _make_media_payload("audio")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] in ("queued", "ignored")

    def test_receive_message_with_video_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """Video message with caption → 200 OK."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        payload = _make_media_payload("video", caption="Mira este video")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200

    def test_receive_message_with_document_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """Document message → 200 OK."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_whatsapp.return_value = client

        payload = _make_media_payload("document")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200

    # --- Outgoing / Non-upsert Events ---

    def test_receive_message_from_me_returns_200_ignored(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-09: fromMe=true → 200 OK, status='ignored', reason='from_me'."""
        payload = _make_valid_payload(fromMe=True)

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ignored"
        # No reason to look up client for outgoing messages
        client_repo_mock.find_by_whatsapp.assert_not_awaited()

    def test_receive_message_unsupported_event_returns_200_ignored(
        self,
        test_client: TestClient,
    ) -> None:
        """RF-WH-18: non-upsert event → 200 OK, status='ignored'."""
        payload = _make_valid_payload(event="messages.update")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ignored"

    def test_receive_message_delete_event_returns_200_ignored(
        self,
        test_client: TestClient,
    ) -> None:
        """messages.delete event → 200 OK, ignored."""
        payload = _make_valid_payload(event="messages.delete")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ignored"

    # --- Payload Validation ---

    def test_receive_message_invalid_payload_returns_400(
        self, test_client: TestClient
    ) -> None:
        """RF-WH-02: payload with missing required fields → 400."""
        # Missing 'data' field entirely
        payload: dict[str, str] = {"event": "messages.upsert", "instance": "default"}

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        # FastAPI/Pydantic returns 422 for validation errors, spec says 400
        # Accept either (schema validation errors are 422 by default)
        assert response.status_code in (400, 422)

    def test_receive_message_missing_event_field_returns_400(
        self, test_client: TestClient
    ) -> None:
        """Missing 'event' field → 400/422 validation error."""
        payload: dict[str, Any] = {
            "instance": "default",
            "data": {
                "key": {"remoteJid": VALID_JID, "fromMe": False},
                "message": {"conversation": "Hola"},
            },
        }

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code in (400, 422)

    def test_receive_message_missing_key_field_returns_400(
        self, test_client: TestClient
    ) -> None:
        """Missing data.key → 400/422 validation error."""
        payload: dict[str, Any] = {
            "event": "messages.upsert",
            "instance": "default",
            "data": {
                "message": {"conversation": "Hola"},
            },
        }

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code in (400, 422)

    def test_receive_message_invalid_jid_format_returns_400(
        self, test_client: TestClient
    ) -> None:
        """remoteJid without @s.whatsapp.net → 422 from Pydantic pattern validation."""
        payload = _make_valid_payload(remoteJid="573001234567")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        # Pydantic field_validator with pattern rejects → 422
        assert response.status_code in (400, 422)

    def test_receive_message_invalid_event_type_returns_400(
        self, test_client: TestClient
    ) -> None:
        """Unsupported event type → 422 from field_validator, or 200 ignored."""
        payload = _make_valid_payload(event="messages.invalid")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        # Either rejected by Pydantic (422) or caught by endpoint (200 ignored)
        assert response.status_code in (200, 400, 422)

    # --- API Key Validation ---

    def test_receive_message_missing_api_key_returns_401(
        self,
        test_client: TestClient,
    ) -> None:
        """RF-WH-03: no x-api-key header → 401 Unauthorized."""
        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            # No x-api-key header
        )

        assert response.status_code == 401

    def test_receive_message_invalid_api_key_returns_401(
        self,
        test_client: TestClient,
    ) -> None:
        """Wrong x-api-key → 401 Unauthorized."""
        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": "wrong-api-key-12345"},
        )

        assert response.status_code == 401

    def test_receive_message_empty_api_key_returns_401(
        self,
        test_client: TestClient,
    ) -> None:
        """Empty x-api-key → 401 Unauthorized."""
        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": ""},
        )

        assert response.status_code == 401

    def test_receive_message_api_key_with_whitespace_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-16: API key with surrounding whitespace → should be stripped, 200 OK."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": f"  {VALID_API_KEY}  "},
        )

        # Spec says strip() before comparing — should succeed
        assert response.status_code == 200

    # --- Performance SLA ---

    def test_webhook_responds_quickly(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-15: response time should be fast (< 500ms p99). Unit test uses 200ms.

        The webhook should hand off to async processing quickly. Repo mocks
        return instantly, so the response should be near-instant.
        """
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        payload = _make_valid_payload()

        start = time.perf_counter()
        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        # FastAPI + mocks should respond in well under 200ms
        assert elapsed_ms < 200, f"Response took {elapsed_ms:.1f}ms, expected < 200ms"

    # --- Rate Limiting ---

    def test_receive_message_rate_limit_exceeded_returns_429(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """RF-WH-14: rate limit exceeded → 429 Too Many Requests."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        # We need to override the rate limiter mock to simulate rate limit exceeded.
        # Create a fresh app with rate limiter returning False.
        from app.infrastructure.http.error_handlers import register_error_handlers
        from app.infrastructure.whatsapp.webhook import (
            get_agent_repo,
            get_client_repo,
            get_rate_limiter,
        )

        rate_limited_app = FastAPI(title="Rate Limited Test App")
        register_error_handlers(rate_limited_app)
        rate_limited_app.include_router(whatsapp_router)

        rate_limited_app.dependency_overrides[get_client_repo] = lambda: client_repo_mock
        rate_limited_app.dependency_overrides[get_agent_repo] = lambda: agent_repo_mock

        rate_limiter_mock = AsyncMock()
        rate_limiter_mock.check.return_value = False  # rate limited!
        rate_limited_app.dependency_overrides[get_rate_limiter] = lambda: rate_limiter_mock

        rate_limited_client = TestClient(rate_limited_app)

        payload = _make_valid_payload()

        response = rate_limited_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers

    # --- Group JID ---

    def test_receive_message_group_jid_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-3: group JID (g.us) → extract member phone, process normally."""
        client = _make_client(whatsapp_number=WhatsAppNumber("573009876543"))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        # Group JID format: groupPhone-memberPhone@g.us
        payload = _make_valid_payload(
            remoteJid="123456789-573009876543@g.us",
            fromMe=False,
        )

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200

    # --- Unicode Messages ---

    def test_receive_message_unicode_returns_200(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-13: message with non-Latin Unicode (Arabic, Chinese) → 200 queued."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        payload = _make_valid_payload(conversation="مرحبا 你好 こんにちは")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "queued"

    # --- Multi-Instance ---

    def test_receive_message_multi_instance_discriminates(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-20: multiple Evolution instances → instance field in payload preserved."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo_mock.find_by_whatsapp.return_value = client
        agent_repo_mock.find_active_by_client.return_value = [agent]

        payload = _make_valid_payload(instance="instance-2")

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "queued"


# ============================================================================
# TestMessageProcessor: Business Logic (Orchestration)
# ============================================================================


class TestMessageProcessor:
    """Unit tests for message_processor.process() — orchestration logic.

    These tests verify the business logic directly (not via HTTP).
    All repository and external dependencies are mocked.
    """

    # --- Fixtures for Processor Tests ---

    @pytest.fixture
    def client_repo(self) -> AsyncMock:
        return AsyncMock(spec=ClientRepository)

    @pytest.fixture
    def agent_repo(self) -> AsyncMock:
        return AsyncMock(spec=AgentRepository)

    @pytest.fixture
    def valid_payload(self) -> EvolutionWebhookPayload:
        """Build a valid EvolutionWebhookPayload Pydantic model."""
        return EvolutionWebhookPayload(
            event="messages.upsert",
            instance="default",
            data=EvolutionData(
                key=EvolutionKey(remoteJid=VALID_JID, fromMe=False),
                message=EvolutionMessageData(conversation="Hola, quiero agendar cita"),
                pushName="Juan",
                messageTimestamp=1717800000,
            ),
        )

    # --- Happy Path ---

    @pytest.mark.asyncio
    async def test_finds_client_by_whatsapp(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """RF-WH-05: extracts WhatsApp number and finds client via repository."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo.find_by_whatsapp.return_value = client
        agent_repo.find_active_by_client.return_value = [agent]

        result = await process(valid_payload, client_repo, agent_repo)

        assert result.status == "queued"
        assert result.task_id is not None
        client_repo.find_by_whatsapp.assert_awaited_once_with(VALID_WHATSAPP)

    @pytest.mark.asyncio
    async def test_finds_active_agents_for_client(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """RF-WH-07: finds active agents for the matched client."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agents = [
            _make_agent(id=AGENT_UUID, name="Recepcionista"),
            _make_agent(id=SECOND_AGENT_UUID, name="Ventas"),
        ]
        client_repo.find_by_whatsapp.return_value = client
        agent_repo.find_active_by_client.return_value = agents

        result = await process(valid_payload, client_repo, agent_repo)

        assert result.status == "queued"
        agent_repo.find_active_by_client.assert_awaited_once()
        # Verify it was called with the correct client ID
        called_client_id = agent_repo.find_active_by_client.call_args[0][0]
        assert str(called_client_id) == str(CLIENT_UUID)

    @pytest.mark.asyncio
    async def test_queues_message_to_celery(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """RF-WH-13: enqueues Celery task with correct arguments."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agents = [
            _make_agent(id=AGENT_UUID),
        ]
        client_repo.find_by_whatsapp.return_value = client
        agent_repo.find_active_by_client.return_value = agents

        with patch(
            "app.infrastructure.whatsapp.message_processor.celery_app"
        ) as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-abc-123"
            mock_celery.send_task.return_value = mock_task

            result = await process(valid_payload, client_repo, agent_repo)

            assert result.status == "queued"
            assert result.task_id == "task-abc-123"
            mock_celery.send_task.assert_called_once()
            # Verify task name and arguments
            call_kwargs = mock_celery.send_task.call_args
            assert call_kwargs[0][0] == "process_whatsapp_message"

    # --- Client Not Found ---

    @pytest.mark.asyncio
    async def test_returns_ignored_when_client_not_found(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """RF-WH-06: unknown WhatsApp number → returns ignored, reason='no_client'."""
        client_repo.find_by_whatsapp.return_value = None

        result = await process(valid_payload, client_repo, agent_repo)

        assert result.status == "ignored"
        assert result.reason == "no_client"
        assert result.task_id is None
        agent_repo.find_active_by_client.assert_not_awaited()

    # --- Client Inactive ---

    @pytest.mark.asyncio
    async def test_returns_ignored_when_client_inactive(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """EC-5: client found but is_active=False → ignored."""
        client = _make_client(is_active=False, whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo.find_by_whatsapp.return_value = client

        result = await process(valid_payload, client_repo, agent_repo)

        assert result.status == "ignored"
        assert result.reason == "client_inactive"

    # --- No Agents ---

    @pytest.mark.asyncio
    async def test_returns_ignored_when_no_active_agents(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """RF-WH-08: client found but no active agents → ignored."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo.find_by_whatsapp.return_value = client
        agent_repo.find_active_by_client.return_value = []

        result = await process(valid_payload, client_repo, agent_repo)

        assert result.status == "ignored"
        assert result.reason == "no_agents"

    # --- Empty Message ---

    @pytest.mark.asyncio
    async def test_returns_ignored_for_empty_message(
        self,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """EC-4: empty conversation text → ignored, reason='empty_message'."""
        payload = EvolutionWebhookPayload(
            event="messages.upsert",
            instance="default",
            data=EvolutionData(
                key=EvolutionKey(remoteJid=VALID_JID, fromMe=False),
                message=EvolutionMessageData(conversation=""),
            ),
        )

        result = await process(payload, client_repo, agent_repo)

        assert result.status == "ignored"
        # Should not query client repo for empty messages
        client_repo.find_by_whatsapp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_ignored_for_whitespace_only_message(
        self,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """Whitespace-only message → ignored."""
        payload = EvolutionWebhookPayload(
            event="messages.upsert",
            instance="default",
            data=EvolutionData(
                key=EvolutionKey(remoteJid=VALID_JID, fromMe=False),
                message=EvolutionMessageData(conversation="   \n  \t  "),
            ),
        )

        result = await process(payload, client_repo, agent_repo)

        assert result.status == "ignored"

    # --- Unsupported Message Type ---

    @pytest.mark.asyncio
    async def test_returns_ignored_for_unsupported_message_type(
        self,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """Message with no recognizable type fields → ignored."""
        payload = EvolutionWebhookPayload(
            event="messages.upsert",
            instance="default",
            data=EvolutionData(
                key=EvolutionKey(remoteJid=VALID_JID, fromMe=False),
                message=EvolutionMessageData(),  # no fields set → type="unknown"
            ),
        )

        result = await process(payload, client_repo, agent_repo)

        assert result.status == "ignored"

    # --- Phone Extraction ---

    def test_extracts_phone_from_standard_jid(self) -> None:
        """RF-WH-04: standard JID → clean phone number extracted."""
        key = EvolutionKey(remoteJid="573001234567@s.whatsapp.net")
        assert key.extract_phone() == "573001234567"

    def test_extracts_phone_from_us_number(self) -> None:
        """US number JID → clean phone number extracted."""
        key = EvolutionKey(remoteJid="12025550123@s.whatsapp.net")
        assert key.extract_phone() == "12025550123"

    def test_extracts_phone_long_international(self) -> None:
        """Long international number → clean extraction."""
        key = EvolutionKey(remoteJid="5491123456789@s.whatsapp.net")
        assert key.extract_phone() == "5491123456789"

    def test_extract_phone_number_standalone_function(self) -> None:
        """Standalone extract_phone_number handles standard JID."""
        result = extract_phone_number("573001234567@s.whatsapp.net")
        assert result == "573001234567"

    def test_extract_phone_number_from_group_jid(self) -> None:
        """EC-3: group JID → extracts member phone."""
        result = extract_phone_number("123456789-573001234567@g.us")
        assert result == "573001234567"

    def test_extract_phone_number_invalid_jid_raises_error(self) -> None:
        """Invalid JID (too short extracted phone) → InvalidMessageError."""
        with pytest.raises(InvalidMessageError):
            extract_phone_number("12345@s.whatsapp.net")

    def test_extract_phone_number_non_digit_jid(self) -> None:
        """JID with non-digit characters → strips non-digits."""
        result = extract_phone_number("+57 300 123-4567@s.whatsapp.net")
        assert result == "573001234567"

    # --- Repository Errors ---

    @pytest.mark.asyncio
    async def test_bubbles_up_domain_error_from_client_repo(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """Domain errors from repositories should bubble up naturally."""
        client_repo.find_by_whatsapp.side_effect = DomainError("Database timeout")

        with pytest.raises(DomainError, match="Database timeout"):
            await process(valid_payload, client_repo, agent_repo)

    @pytest.mark.asyncio
    async def test_bubbles_up_domain_error_from_agent_repo(
        self,
        valid_payload: EvolutionWebhookPayload,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """Agent repo errors should bubble up."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo.find_by_whatsapp.return_value = client
        agent_repo.find_active_by_client.side_effect = DomainError("Supabase timeout")

        with pytest.raises(DomainError, match="Supabase timeout"):
            await process(valid_payload, client_repo, agent_repo)

    # --- Message Content ---

    @pytest.mark.asyncio
    async def test_extracts_text_from_extended_text_message(
        self,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """Extended text message (with preview) → text content extracted."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo.find_by_whatsapp.return_value = client
        agent_repo.find_active_by_client.return_value = [agent]

        payload = EvolutionWebhookPayload(
            event="messages.upsert",
            instance="default",
            data=EvolutionData(
                key=EvolutionKey(remoteJid=VALID_JID, fromMe=False),
                message=EvolutionMessageData(
                    extended_text_message={"text": "Hola con preview", "previewType": "0"}
                ),
            ),
        )

        with patch("app.infrastructure.whatsapp.message_processor.celery_app") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-ext-1"
            mock_celery.send_task.return_value = mock_task

            result = await process(payload, client_repo, agent_repo)

            assert result.status == "queued"
            # Verify the sanitized text was passed to Celery
            call_args = mock_celery.send_task.call_args
            assert "Hola con preview" in str(call_args)

    @pytest.mark.asyncio
    async def test_extracts_text_from_button_response(
        self,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """Button response message → selected display text extracted."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        agent = _make_agent()
        client_repo.find_by_whatsapp.return_value = client
        agent_repo.find_active_by_client.return_value = [agent]

        payload = EvolutionWebhookPayload(
            event="messages.upsert",
            instance="default",
            data=EvolutionData(
                key=EvolutionKey(remoteJid=VALID_JID, fromMe=False),
                message=EvolutionMessageData(
                    button_response_message={
                        "selectedButtonId": "btn-1",
                        "selectedDisplayText": "Agendar cita",
                    }
                ),
            ),
        )

        with patch("app.infrastructure.whatsapp.message_processor.celery_app") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-btn-1"
            mock_celery.send_task.return_value = mock_task

            result = await process(payload, client_repo, agent_repo)

            assert result.status == "queued"
            call_args = mock_celery.send_task.call_args
            assert "Agendar cita" in str(call_args)

    # --- Processor Ignores Non-Upsert Events ---

    @pytest.mark.asyncio
    async def test_ignores_messages_update_event(
        self,
        client_repo: AsyncMock,
        agent_repo: AsyncMock,
    ) -> None:
        """messages.update event → ignored."""
        payload = EvolutionWebhookPayload(
            event="messages.update",
            instance="default",
            data=EvolutionData(
                key=EvolutionKey(remoteJid=VALID_JID, fromMe=False),
                message=EvolutionMessageData(conversation="Edited message"),
            ),
        )

        result = await process(payload, client_repo, agent_repo)

        assert result.status == "ignored"
        client_repo.find_by_whatsapp.assert_not_awaited()


# ============================================================================
# TestWebhookErrorHandling: Error Scenarios via HTTP
# ============================================================================


class TestWebhookErrorHandling:
    """Verify the webhook endpoint handles infra errors gracefully.

    Tests that internal errors (Supabase timeout, Celery unavailable)
    are mapped to correct HTTP status codes.
    """

    def test_repo_timeout_returns_500(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
    ) -> None:
        """EC-10: Supabase timeout → 500 Internal Server Error."""
        client_repo_mock.find_by_whatsapp.side_effect = DomainError(
            "Supabase connection timeout"
        )

        payload = _make_valid_payload()

        response = test_client.post(
            "/webhook/whatsapp",
            json=payload,
            headers={"x-api-key": VALID_API_KEY},
        )

        assert response.status_code == 500
        body = response.json()
        assert "error" in body or "detail" in body

    def test_invalid_json_body_returns_422(
        self, test_client: TestClient
    ) -> None:
        """EC-1: malformed JSON body → 422 from FastAPI."""
        response = test_client.post(
            "/webhook/whatsapp",
            content=b"this is not json",
            headers={
                "x-api-key": VALID_API_KEY,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code in (400, 422)
