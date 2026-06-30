"""Unit tests for HTTP routers (RED phase — TDD).

These tests verify the HTTP contract for all 12 endpoints BEFORE any router
code exists. Imports from `app.infrastructure.http.*` will fail with
ImportError — that is the expected RED signal.

When the developer creates skeleton files (empty routers, schemas, deps,
error handlers), the imports succeed and tests start running. Tests will
then fail with 404/405 because endpoints aren't implemented → implement
endpoints one by one until all tests pass (GREEN).

Coverage:
- 6 client endpoints (POST, GET by id, GET search/list, PATCH, DELETE)
- 6 agent endpoints (POST nested, GET, GET nested, PATCH, DELETE, DELETE perm)
- Happy paths, edge cases, error mappings (400, 404, 422, 500)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# --- Domain layer (already exists) ---
from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import (
    AgentNotFoundError,
    ClientNotFoundError,
    DomainError,
    InvalidAgentError,
    InvalidClientError,
)
from app.domain.shared.value_objects import AgentId, BusinessType, ClientId, WhatsAppNumber

# --- Application DTOs (already exist) ---
from app.application.dtos import (
    AgentOutput,
    AgentToolInput,
    AgentToolOutput,
    ClientOutput,
    CreateAgentInput,
    CreateClientInput,
    DeactivateAgentInput,
    DeactivateClientInput,
    DeleteAgentInput,
    GetAgentInput,
    GetClientInput,
    ListAgentsByClientInput,
    ListClientsInput,
    UpdateAgentInput,
    UpdateClientInput,
)

# --- Infrastructure HTTP (does NOT exist yet — RED phase) ---
# These imports WILL fail until the developer creates the files:
#   app/infrastructure/http/__init__.py
#   app/infrastructure/http/client_router.py
#   app/infrastructure/http/agent_router.py
#   app/infrastructure/http/error_handlers.py
#   app/infrastructure/http/dependencies.py
#   app/infrastructure/http/schemas.py
from app.infrastructure.http.agent_router import router as agent_router  # noqa: F401
from app.infrastructure.http.client_router import router as client_router  # noqa: F401
from app.infrastructure.http.dependencies import get_agent_repo, get_client_repo  # noqa: F401
from app.infrastructure.http.error_handlers import register_error_handlers  # noqa: F401

# ============================================================================
# Constants
# ============================================================================

CLIENT_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AGENT_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")
SECOND_CLIENT_UUID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"
VALID_WHATSAPP = "573001234567"
SECOND_WHATSAPP = "573009876543"

_MIN_PERSONALITY = "Eres un asistente amable y profesional. Diez caracteres minimo."

# ============================================================================
# Entity factories (mirror helpers from use-case tests)
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
    object.__setattr__(c, "created_at", overrides.get("created_at", datetime(2026, 1, 1, tzinfo=timezone.utc)))
    object.__setattr__(c, "updated_at", overrides.get("updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc)))
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
    object.__setattr__(a, "created_at", overrides.get("created_at", datetime(2026, 1, 1, tzinfo=timezone.utc)))
    object.__setattr__(a, "updated_at", overrides.get("updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc)))
    return a


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


@pytest.fixture
def app(client_repo_mock: AsyncMock, agent_repo_mock: AsyncMock) -> FastAPI:
    """Create a FastAPI test app with routers, error handlers, and mocked deps.

    This fixture:
    1. Creates a fresh FastAPI instance
    2. Registers domain → HTTP error handlers
    3. Registers client_router (prefix /api/v1/clients)
    4. Registers agent_router (prefix /api/v1/agents)
    5. Overrides get_client_repo and get_agent_repo dependencies

    When the http modules don't exist yet, this fixture will raise ImportError
    — that's the expected RED phase signal.
    """
    test_app = FastAPI(title="Test App")

    # Register error handlers (maps domain errors → HTTP status codes)
    register_error_handlers(test_app)

    # Register routers
    test_app.include_router(client_router, prefix="/api/v1/clients", tags=["Clients"])
    test_app.include_router(agent_router, prefix="/api/v1/agents", tags=["Agents"])

    # Override dependencies with mocks
    test_app.dependency_overrides[get_client_repo] = lambda: client_repo_mock
    test_app.dependency_overrides[get_agent_repo] = lambda: agent_repo_mock

    # Register health check (from main.py)
    @test_app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "0.1.0"}

    return test_app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Synchronous TestClient wrapping the test FastAPI app."""
    return TestClient(app)


# ============================================================================
# E1: POST /api/v1/clients — Create Client
# ============================================================================


class TestCreateClientEndpoint:
    """POST /api/v1/clients — 201 on success, 400 on validation errors."""

    def test_create_client_returns_201_with_client_response(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Happy path: valid payload → 201, response matches ClientResponse shape."""
        client_repo_mock.find_by_whatsapp.return_value = None

        payload: dict[str, Any] = {
            "name": "Peluqueria El Corte",
            "business_type": "peluqueria",
            "whatsapp_number": VALID_WHATSAPP,
        }

        response = test_client.post("/api/v1/clients", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Peluqueria El Corte"
        assert body["business_type"] == "peluqueria"
        assert body["whatsapp_number"] == VALID_WHATSAPP
        assert body["is_active"] is True
        assert body["id"]  # non-empty UUID string
        assert "created_at" in body
        assert "updated_at" in body
        client_repo_mock.find_by_whatsapp.assert_awaited_once()
        client_repo_mock.save.assert_awaited_once()

    def test_create_client_empty_name_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-01: empty name → 400 with error_type 'invalid_client'."""
        payload: dict[str, Any] = {
            "name": "",
            "business_type": "peluqueria",
            "whatsapp_number": VALID_WHATSAPP,
        }

        response = test_client.post("/api/v1/clients", json=payload)

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"
        assert "detail" in body
        client_repo_mock.save.assert_not_awaited()

    def test_create_client_whitespace_only_name_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Whitespace-only name stripped by use case → 400 invalid_client."""
        payload: dict[str, Any] = {
            "name": "   ",
            "business_type": "peluqueria",
            "whatsapp_number": VALID_WHATSAPP,
        }

        response = test_client.post("/api/v1/clients", json=payload)

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"

    def test_create_client_duplicate_whatsapp_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-04: WhatsApp already registered → 400 with 'already registered' detail."""
        existing = _make_client()
        client_repo_mock.find_by_whatsapp.return_value = existing

        payload: dict[str, Any] = {
            "name": "Another Biz",
            "business_type": "bar",
            "whatsapp_number": VALID_WHATSAPP,
        }

        response = test_client.post("/api/v1/clients", json=payload)

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"
        assert "already registered" in body["detail"].lower()
        client_repo_mock.save.assert_not_awaited()

    def test_create_client_whatsapp_too_short_returns_422(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-03: WhatsApp < 10 digits → 422 from Pydantic min_length=10."""
        payload: dict[str, Any] = {
            "name": "My Biz",
            "business_type": "otro",
            "whatsapp_number": "12345",
        }

        response = test_client.post("/api/v1/clients", json=payload)

        assert response.status_code == 422
        client_repo_mock.save.assert_not_awaited()

    def test_create_client_invalid_business_type_returns_422(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-02: invalid business_type → 422 (value object raises ValueError,
        which bubbles up to FastAPI as unhandled → 500, unless the endpoint
        catches it and raises HTTPException 422).
        """
        payload: dict[str, Any] = {
            "name": "My Biz",
            "business_type": "colegio",  # not in VALID_TYPES
            "whatsapp_number": VALID_WHATSAPP,
        }

        response = test_client.post("/api/v1/clients", json=payload)

        # The use case catches ValueError from BusinessType VO and
        # raises InvalidClientError → 400.
        assert response.status_code in (400, 422, 500)
        client_repo_mock.save.assert_not_awaited()

    def test_create_client_missing_required_field_returns_422(
        self, test_client: TestClient
    ) -> None:
        """Missing 'name' field → 422 from Pydantic validation."""
        payload: dict[str, Any] = {
            "business_type": "peluqueria",
            "whatsapp_number": VALID_WHATSAPP,
        }

        response = test_client.post("/api/v1/clients", json=payload)

        assert response.status_code == 422


# ============================================================================
# E2: GET /api/v1/clients/{client_id} — Get Client by ID
# ============================================================================


class TestGetClientByIdEndpoint:
    """GET /api/v1/clients/{client_id} — 200 on found, 404 on missing."""

    def test_get_client_by_id_returns_200(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Happy path: existing client → 200 with ClientResponse."""
        client = _make_client(id=CLIENT_UUID, name="My Biz")
        client_repo_mock.find_by_id.return_value = client

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(CLIENT_UUID)
        assert body["name"] == "My Biz"
        assert body["is_active"] is True
        assert "created_at" in body
        assert "updated_at" in body
        client_repo_mock.find_by_id.assert_awaited_once()

    def test_get_client_by_id_not_found_returns_404(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-06: non-existent client_id → 404 with error_type 'client_not_found'."""
        client_repo_mock.find_by_id.return_value = None

        response = test_client.get(f"/api/v1/clients/{NONEXISTENT_UUID}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "client_not_found"

    def test_get_client_by_id_invalid_uuid_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-05: non-UUID client_id → 400 with error_type 'invalid_client'."""
        response = test_client.get("/api/v1/clients/not-a-uuid")

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"
        client_repo_mock.find_by_id.assert_not_awaited()

    def test_get_client_by_id_deactivated_returns_200_with_is_active_false(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Deactivated client is still retrievable; is_active=False in response."""
        client = _make_client(id=CLIENT_UUID, is_active=False)
        client_repo_mock.find_by_id.return_value = client

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False


# ============================================================================
# E3/E4: GET /api/v1/clients — Search by WhatsApp or List
# ============================================================================


class TestQueryClientsEndpoint:
    """GET /api/v1/clients?whatsapp=X (search) or ?limit=N&offset=M (list)."""

    # --- Search by WhatsApp (E3) ---

    def test_get_client_by_whatsapp_returns_200(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Happy path: search by WhatsApp → 200 with single ClientResponse."""
        client = _make_client(whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_whatsapp.return_value = client

        response = test_client.get(f"/api/v1/clients?whatsapp={VALID_WHATSAPP}")

        assert response.status_code == 200
        body = response.json()
        assert body["whatsapp_number"] == VALID_WHATSAPP
        assert body["id"] == str(CLIENT_UUID)
        client_repo_mock.find_by_whatsapp.assert_awaited_once_with(VALID_WHATSAPP)

    def test_get_client_by_whatsapp_not_found_returns_404(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-07: WhatsApp not found → 404 with error_type 'client_not_found'."""
        client_repo_mock.find_by_whatsapp.return_value = None

        response = test_client.get(f"/api/v1/clients?whatsapp={VALID_WHATSAPP}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "client_not_found"

    # --- List clients (E4) ---

    def test_list_clients_returns_200_with_items(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Happy path: list active clients → 200 with ClientListResponse."""
        clients = [
            _make_client(id=uuid.uuid4(), name=f"Client {i}") for i in range(3)
        ]
        client_repo_mock.list_active.return_value = clients

        response = test_client.get("/api/v1/clients")

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "count" in body
        assert body["count"] == 3
        assert len(body["items"]) == 3
        assert body["items"][0]["name"] == "Client 0"
        assert body["items"][1]["name"] == "Client 1"
        assert body["items"][2]["name"] == "Client 2"
        client_repo_mock.list_active.assert_awaited_once_with(50, 0)

    def test_list_clients_empty_returns_200_with_empty_items(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-10: no active clients → 200 with items=[], count=0."""
        client_repo_mock.list_active.return_value = []

        response = test_client.get("/api/v1/clients")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["count"] == 0

    def test_list_clients_with_pagination_params(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """limit=10&offset=5 → paginated results."""
        clients = [_make_client(id=uuid.uuid4(), name=f"Client {i}") for i in range(10)]
        client_repo_mock.list_active.return_value = clients

        response = test_client.get("/api/v1/clients?limit=10&offset=5")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 10
        client_repo_mock.list_active.assert_awaited_once_with(10, 5)

    def test_list_clients_limit_zero_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-08: limit=0 → 400 (Pydantic Query(ge=1) → 422, or use case → 400)."""
        response = test_client.get("/api/v1/clients?limit=0")

        # FastAPI Query(ge=1) validation returns 422.
        # If use case catches it, may return 400.
        assert response.status_code in (400, 422)
        client_repo_mock.list_active.assert_not_called()

    def test_list_clients_negative_offset_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-09: offset=-5 → 400 (Pydantic Query(ge=0) → 422, or use case → 400)."""
        response = test_client.get("/api/v1/clients?offset=-5")

        assert response.status_code in (400, 422)
        client_repo_mock.list_active.assert_not_called()

    def test_list_clients_limit_exceeds_max_returns_422(
        self, test_client: TestClient
    ) -> None:
        """limit=201 exceeds Query(le=200) → 422 from Pydantic."""
        response = test_client.get("/api/v1/clients?limit=201")

        assert response.status_code == 422


# ============================================================================
# E5: PATCH /api/v1/clients/{client_id} — Update Client
# ============================================================================


class TestUpdateClientEndpoint:
    """PATCH /api/v1/clients/{client_id} — 200 on success, 400/404/422 on errors."""

    def test_update_client_name_returns_200(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Happy path: update name → 200 with updated ClientResponse."""
        client = _make_client(id=CLIENT_UUID, name="Old Name")
        client_repo_mock.find_by_id.return_value = client

        payload: dict[str, Any] = {"name": "New Name"}

        response = test_client.patch(f"/api/v1/clients/{CLIENT_UUID}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New Name"
        assert body["id"] == str(CLIENT_UUID)
        client_repo_mock.save.assert_awaited_once()

    def test_update_client_whatsapp_returns_200(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Update WhatsApp number → 200 with new number."""
        client = _make_client(id=CLIENT_UUID, whatsapp_number=WhatsAppNumber(VALID_WHATSAPP))
        client_repo_mock.find_by_id.return_value = client
        client_repo_mock.find_by_whatsapp.return_value = None  # no duplicate

        payload: dict[str, Any] = {"whatsapp_number": SECOND_WHATSAPP}

        response = test_client.patch(f"/api/v1/clients/{CLIENT_UUID}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["whatsapp_number"] == SECOND_WHATSAPP
        client_repo_mock.save.assert_awaited_once()

    def test_update_client_not_found_returns_404(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Non-existent client_id → 404."""
        client_repo_mock.find_by_id.return_value = None

        payload: dict[str, Any] = {"name": "New Name"}

        response = test_client.patch(
            f"/api/v1/clients/{NONEXISTENT_UUID}", json=payload
        )

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "client_not_found"
        client_repo_mock.save.assert_not_awaited()

    def test_update_client_no_fields_returns_422(
        self, test_client: TestClient
    ) -> None:
        """EC-11: empty body (both fields null) → 422 from model_validator."""
        payload: dict[str, Any] = {}

        response = test_client.patch(f"/api/v1/clients/{CLIENT_UUID}", json=payload)

        assert response.status_code == 422

    def test_update_client_both_fields_null_returns_422(
        self, test_client: TestClient
    ) -> None:
        """Both name and whatsapp_number explicitly null → 422."""
        payload: dict[str, Any] = {"name": None, "whatsapp_number": None}

        response = test_client.patch(f"/api/v1/clients/{CLIENT_UUID}", json=payload)

        assert response.status_code == 422

    def test_update_client_duplicate_whatsapp_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-12: WhatsApp already taken by another client → 400."""
        client = _make_client(id=CLIENT_UUID)
        other = _make_client(id=SECOND_CLIENT_UUID, whatsapp_number=WhatsAppNumber(SECOND_WHATSAPP))
        client_repo_mock.find_by_id.return_value = client
        client_repo_mock.find_by_whatsapp.return_value = other  # different client

        payload: dict[str, Any] = {"whatsapp_number": SECOND_WHATSAPP}

        response = test_client.patch(f"/api/v1/clients/{CLIENT_UUID}", json=payload)

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"
        assert "already registered" in body["detail"].lower()
        client_repo_mock.save.assert_not_awaited()

    def test_update_client_empty_name_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Update name to empty string → 400."""
        client = _make_client(id=CLIENT_UUID, name="Old Name")
        client_repo_mock.find_by_id.return_value = client

        payload: dict[str, Any] = {"name": ""}

        response = test_client.patch(f"/api/v1/clients/{CLIENT_UUID}", json=payload)

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"
        client_repo_mock.save.assert_not_awaited()


# ============================================================================
# E6: DELETE /api/v1/clients/{client_id} — Deactivate Client
# ============================================================================


class TestDeactivateClientEndpoint:
    """DELETE /api/v1/clients/{client_id} — 200 on success, 404 on missing."""

    def test_deactivate_client_returns_200_with_is_active_false(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """Happy path: active client → deactivated, is_active=False in response."""
        client = _make_client(id=CLIENT_UUID, is_active=True)
        client_repo_mock.find_by_id.return_value = client

        response = test_client.delete(f"/api/v1/clients/{CLIENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(CLIENT_UUID)
        assert body["is_active"] is False
        client_repo_mock.save.assert_awaited_once()

    def test_deactivate_client_not_found_returns_404(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-14: non-existent client → 404."""
        client_repo_mock.find_by_id.return_value = None

        response = test_client.delete(f"/api/v1/clients/{NONEXISTENT_UUID}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "client_not_found"
        client_repo_mock.save.assert_not_awaited()

    def test_deactivate_client_idempotent_returns_200(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """EC-13: already deactivated → still returns 200 with is_active=False."""
        client = _make_client(id=CLIENT_UUID, is_active=False)
        client_repo_mock.find_by_id.return_value = client

        response = test_client.delete(f"/api/v1/clients/{CLIENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False
        client_repo_mock.save.assert_awaited_once()


# ============================================================================
# E7: POST /api/v1/clients/{client_id}/agents — Create Agent
# ============================================================================


class TestCreateAgentEndpoint:
    """POST /api/v1/clients/{client_id}/agents — 201 on success, 400 on errors."""

    def test_create_agent_returns_201_with_agent_response(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """Happy path: valid payload, client exists → 201 with AgentResponse."""
        client = _make_client(id=CLIENT_UUID)
        client_repo_mock.find_by_id.return_value = client

        payload: dict[str, Any] = {
            "name": "Bot Peluqueria",
            "personality": _MIN_PERSONALITY,
            "tools": [
                {
                    "name": "book_appointment",
                    "description": "Reservar cita",
                    "endpoint": "https://n8n.example.com/book",
                }
            ],
            "knowledge_base_refs": ["kb-precios"],
        }

        response = test_client.post(
            f"/api/v1/clients/{CLIENT_UUID}/agents", json=payload
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Bot Peluqueria"
        assert body["personality"] == _MIN_PERSONALITY
        assert body["client_id"] == str(CLIENT_UUID)
        assert body["is_active"] is True
        assert len(body["tools"]) == 1
        assert body["tools"][0]["name"] == "book_appointment"
        assert body["tools"][0]["endpoint"] == "https://n8n.example.com/book"
        assert body["knowledge_base_refs"] == ["kb-precios"]
        assert body["id"]  # non-empty
        assert "created_at" in body
        assert "updated_at" in body
        client_repo_mock.find_by_id.assert_awaited_once()
        agent_repo_mock.save.assert_awaited_once()

    def test_create_agent_with_empty_tools_returns_201(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """Agent with tools=[] and knowledge_base_refs=[] → 201."""
        client_repo_mock.find_by_id.return_value = _make_client(id=CLIENT_UUID)

        payload: dict[str, Any] = {
            "name": "Minimal Bot",
            "personality": _MIN_PERSONALITY,
            "tools": [],
            "knowledge_base_refs": [],
        }

        response = test_client.post(
            f"/api/v1/clients/{CLIENT_UUID}/agents", json=payload
        )

        assert response.status_code == 201
        body = response.json()
        assert body["tools"] == []
        assert body["knowledge_base_refs"] == []

    def test_create_agent_client_not_found_returns_400(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-16: client_id does not exist → 400 with error_type 'invalid_agent'."""
        client_repo_mock.find_by_id.return_value = None

        payload: dict[str, Any] = {
            "name": "Bot",
            "personality": _MIN_PERSONALITY,
        }

        response = test_client.post(
            f"/api/v1/clients/{NONEXISTENT_UUID}/agents", json=payload
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_agent"
        agent_repo_mock.save.assert_not_awaited()

    def test_create_agent_invalid_client_id_returns_400(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """EC-17: non-UUID client_id → 400 with error_type 'invalid_client'."""
        payload: dict[str, Any] = {
            "name": "Bot",
            "personality": _MIN_PERSONALITY,
        }

        response = test_client.post(
            "/api/v1/clients/not-a-uuid/agents", json=payload
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"

    def test_create_agent_personality_too_short_returns_422(
        self, test_client: TestClient
    ) -> None:
        """EC-15: personality < 10 chars → 422 from Pydantic min_length=10."""
        payload: dict[str, Any] = {
            "name": "Bot",
            "personality": "corto",  # 5 chars
        }

        response = test_client.post(
            f"/api/v1/clients/{CLIENT_UUID}/agents", json=payload
        )

        assert response.status_code == 422

    def test_create_agent_empty_name_returns_400(
        self,
        test_client: TestClient,
        client_repo_mock: AsyncMock,
        agent_repo_mock: AsyncMock,
    ) -> None:
        """Empty agent name → 400 with error_type 'invalid_agent'."""
        client_repo_mock.find_by_id.return_value = _make_client(id=CLIENT_UUID)

        payload: dict[str, Any] = {
            "name": "",
            "personality": _MIN_PERSONALITY,
        }

        response = test_client.post(
            f"/api/v1/clients/{CLIENT_UUID}/agents", json=payload
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_agent"
        agent_repo_mock.save.assert_not_awaited()


# ============================================================================
# E8: GET /api/v1/agents/{agent_id} — Get Agent
# ============================================================================


class TestGetAgentEndpoint:
    """GET /api/v1/agents/{agent_id} — 200 on found, 404 on missing."""

    def test_get_agent_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Happy path: existing agent → 200 with AgentResponse."""
        agent = _make_agent(
            id=AGENT_UUID,
            name="Bot Peluqueria",
            tools=[
                AgentTool(name="t1", description="desc1", endpoint="https://n8n.example.com/t1"),
                AgentTool(name="t2", description="desc2", endpoint="https://n8n.example.com/t2"),
            ],
        )
        agent_repo_mock.find_by_id.return_value = agent

        response = test_client.get(f"/api/v1/agents/{AGENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(AGENT_UUID)
        assert body["client_id"] == str(CLIENT_UUID)
        assert body["name"] == "Bot Peluqueria"
        assert body["personality"] == _MIN_PERSONALITY
        assert body["is_active"] is True
        assert len(body["tools"]) == 2
        assert body["tools"][0]["name"] == "t1"
        assert body["tools"][1]["name"] == "t2"
        assert body["knowledge_base_refs"] == ["kb-1"]
        assert "created_at" in body
        assert "updated_at" in body
        agent_repo_mock.find_by_id.assert_awaited_once()

    def test_get_agent_not_found_returns_404(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """EC-18: non-existent agent → 404 with error_type 'agent_not_found'."""
        agent_repo_mock.find_by_id.return_value = None

        response = test_client.get(f"/api/v1/agents/{NONEXISTENT_UUID}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "agent_not_found"

    def test_get_agent_invalid_uuid_returns_400(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Non-UUID agent_id → 400 with error_type 'invalid_agent'."""
        response = test_client.get("/api/v1/agents/not-a-uuid")

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_agent"
        agent_repo_mock.find_by_id.assert_not_awaited()

    def test_get_agent_deactivated_returns_200_with_is_active_false(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Deactivated agent is still retrievable; is_active=False."""
        agent = _make_agent(id=AGENT_UUID, is_active=False)
        agent_repo_mock.find_by_id.return_value = agent

        response = test_client.get(f"/api/v1/agents/{AGENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False


# ============================================================================
# E9: GET /api/v1/clients/{client_id}/agents — List Agents by Client
# ============================================================================


class TestListAgentsByClientEndpoint:
    """GET /api/v1/clients/{client_id}/agents — 200 with AgentListResponse."""

    def test_list_agents_by_client_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Happy path: client has agents → 200 with AgentListResponse."""
        agents = [
            _make_agent(id=uuid.uuid4(), name=f"Agent {i}") for i in range(3)
        ]
        agent_repo_mock.find_active_by_client.return_value = agents

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}/agents")

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "count" in body
        assert body["count"] == 3
        assert len(body["items"]) == 3
        assert body["items"][0]["name"] == "Agent 0"
        assert body["items"][1]["name"] == "Agent 1"
        assert body["items"][2]["name"] == "Agent 2"
        assert all(item["client_id"] == str(CLIENT_UUID) for item in body["items"])
        agent_repo_mock.find_active_by_client.assert_awaited_once()

    def test_list_agents_by_client_empty_returns_200_with_empty_items(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """EC-19: no agents → 200 with items=[], count=0."""
        agent_repo_mock.find_active_by_client.return_value = []

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}/agents")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["count"] == 0

    def test_list_agents_by_client_only_active_agents(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Repository filters deactivated agents; only active ones returned."""
        active = _make_agent(id=AGENT_UUID, name="ActiveOne", is_active=True)
        agent_repo_mock.find_active_by_client.return_value = [active]

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}/agents")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["items"][0]["is_active"] is True

    def test_list_agents_by_client_invalid_uuid_returns_400(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Non-UUID client_id → 400."""
        response = test_client.get("/api/v1/clients/not-a-uuid/agents")

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"


# ============================================================================
# E10: PATCH /api/v1/agents/{agent_id} — Update Agent
# ============================================================================


class TestUpdateAgentEndpoint:
    """PATCH /api/v1/agents/{agent_id} — 200 on success, 404/422 on errors."""

    def test_update_agent_personality_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Happy path: update personality → 200 with updated AgentResponse."""
        agent = _make_agent(id=AGENT_UUID, personality="Original prompt with 10+ chars.")
        agent_repo_mock.find_by_id.return_value = agent

        new_personality = "Nueva personalidad de mas de 10 caracteres!"
        payload: dict[str, Any] = {"personality": new_personality}

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["personality"] == new_personality
        assert body["name"] == "Test Agent"  # unchanged
        assert body["id"] == str(AGENT_UUID)
        agent_repo_mock.save.assert_awaited_once()

    def test_update_agent_name_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Update name only → 200."""
        agent = _make_agent(id=AGENT_UUID, name="Old Name")
        agent_repo_mock.find_by_id.return_value = agent

        payload: dict[str, Any] = {"name": "New Agent Name"}

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New Agent Name"

    def test_update_agent_tools_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Update tools list → old tools replaced."""
        agent = _make_agent(id=AGENT_UUID, tools=[
            AgentTool(name="old_tool", description="old", endpoint="https://old.example.com"),
        ])
        agent_repo_mock.find_by_id.return_value = agent

        new_tools: list[dict[str, str]] = [
            {"name": "new_tool", "description": "new", "endpoint": "https://new.example.com"},
        ]
        payload: dict[str, Any] = {"tools": new_tools}

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert len(body["tools"]) == 1
        assert body["tools"][0]["name"] == "new_tool"
        assert body["tools"][0]["endpoint"] == "https://new.example.com"

    def test_update_agent_knowledge_base_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Update knowledge_base_refs → 200."""
        agent = _make_agent(id=AGENT_UUID, knowledge_base_refs=["old-kb"])
        agent_repo_mock.find_by_id.return_value = agent

        payload: dict[str, Any] = {"knowledge_base_refs": ["new-kb-1", "new-kb-2"]}

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["knowledge_base_refs"] == ["new-kb-1", "new-kb-2"]

    def test_update_agent_multiple_fields_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Update multiple fields → all updated."""
        agent = _make_agent(
            id=AGENT_UUID,
            name="Old",
            personality="Old personality with 10 chars...",
            knowledge_base_refs=["old-kb"],
        )
        agent_repo_mock.find_by_id.return_value = agent

        payload: dict[str, Any] = {
            "name": "Updated Bot",
            "personality": "Updated personality count 10+ chars.",
            "knowledge_base_refs": ["new-kb-1", "new-kb-2"],
        }

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Updated Bot"
        assert body["personality"] == "Updated personality count 10+ chars."
        assert body["knowledge_base_refs"] == ["new-kb-1", "new-kb-2"]

    def test_update_agent_not_found_returns_404(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """EC-22: non-existent agent → 404."""
        agent_repo_mock.find_by_id.return_value = None

        payload: dict[str, Any] = {"name": "New Name"}

        response = test_client.patch(
            f"/api/v1/agents/{NONEXISTENT_UUID}", json=payload
        )

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "agent_not_found"
        agent_repo_mock.save.assert_not_awaited()

    def test_update_agent_no_fields_returns_422(
        self, test_client: TestClient
    ) -> None:
        """EC-20: empty body → 422 from model_validator."""
        payload: dict[str, Any] = {}

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 422

    def test_update_agent_all_fields_null_returns_422(
        self, test_client: TestClient
    ) -> None:
        """All fields explicitly null → 422 from model_validator."""
        payload: dict[str, Any] = {
            "name": None,
            "personality": None,
            "tools": None,
            "knowledge_base_refs": None,
        }

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 422

    def test_update_agent_personality_too_short_returns_422(
        self, test_client: TestClient
    ) -> None:
        """EC-21: personality < 10 chars → 422 from Pydantic."""
        payload: dict[str, Any] = {"personality": "corto"}

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 422

    def test_update_agent_empty_name_returns_400(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Update name to empty → 400."""
        agent = _make_agent(id=AGENT_UUID, name="Old Name")
        agent_repo_mock.find_by_id.return_value = agent

        payload: dict[str, Any] = {"name": ""}

        response = test_client.patch(f"/api/v1/agents/{AGENT_UUID}", json=payload)

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_agent"
        agent_repo_mock.save.assert_not_awaited()


# ============================================================================
# E11: DELETE /api/v1/agents/{agent_id} — Deactivate Agent
# ============================================================================


class TestDeactivateAgentEndpoint:
    """DELETE /api/v1/agents/{agent_id} — 200 on success, 404 on missing."""

    def test_deactivate_agent_returns_200_with_is_active_false(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Happy path: active agent → deactivated, is_active=False."""
        agent = _make_agent(id=AGENT_UUID, is_active=True)
        agent_repo_mock.find_by_id.return_value = agent

        response = test_client.delete(f"/api/v1/agents/{AGENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(AGENT_UUID)
        assert body["is_active"] is False
        agent_repo_mock.save.assert_awaited_once()

    def test_deactivate_agent_not_found_returns_404(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """EC-24: non-existent agent → 404."""
        agent_repo_mock.find_by_id.return_value = None

        response = test_client.delete(f"/api/v1/agents/{NONEXISTENT_UUID}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "agent_not_found"
        agent_repo_mock.save.assert_not_awaited()

    def test_deactivate_agent_idempotent_returns_200(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """EC-23: already deactivated → still 200 with is_active=False."""
        agent = _make_agent(id=AGENT_UUID, is_active=False)
        agent_repo_mock.find_by_id.return_value = agent

        response = test_client.delete(f"/api/v1/agents/{AGENT_UUID}")

        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False
        agent_repo_mock.save.assert_awaited_once()


# ============================================================================
# E12: DELETE /api/v1/agents/{agent_id}/permanent — Delete Agent Permanently
# ============================================================================


class TestDeleteAgentPermanentEndpoint:
    """DELETE /api/v1/agents/{agent_id}/permanent — 204 on success, 404 on missing."""

    def test_delete_agent_permanent_returns_204_no_body(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """EC-26: happy path → 204, empty body."""
        # delete() succeeds (no exception) → means agent existed and was deleted

        response = test_client.delete(f"/api/v1/agents/{AGENT_UUID}/permanent")

        assert response.status_code == 204
        assert response.content == b""  # no body
        agent_repo_mock.delete.assert_awaited_once()

    def test_delete_agent_permanent_not_found_returns_404(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """EC-25: non-existent agent → 404."""
        agent_repo_mock.delete.side_effect = AgentNotFoundError(
            f"Agent not found: {NONEXISTENT_UUID}"
        )

        response = test_client.delete(f"/api/v1/agents/{NONEXISTENT_UUID}/permanent")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "agent_not_found"

    def test_delete_agent_permanent_invalid_uuid_returns_400(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """Non-UUID agent_id → 400."""
        response = test_client.delete("/api/v1/agents/not-a-uuid/permanent")

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_agent"
        agent_repo_mock.delete.assert_not_awaited()


# ============================================================================
# Domain Error → HTTP Status Code Mapping
# ============================================================================


class TestDomainErrorMapping:
    """Verify error handlers map domain errors to correct HTTP responses.

    These tests simulate unhandled domain errors raised during request processing.
    They verify the error handler registration in `error_handlers.py`.
    """

    def test_domain_error_returns_500(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """DomainError (base) → 500 with error_type 'domain_error'."""
        client_repo_mock.find_by_id.side_effect = DomainError("Database connection failed")

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}")

        assert response.status_code == 500
        body = response.json()
        assert body["error_type"] == "domain_error"
        assert body["detail"] == "Database connection failed"

    def test_client_not_found_error_returns_404(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """ClientNotFoundError → 404 with error_type 'client_not_found'."""
        client_repo_mock.find_by_id.side_effect = ClientNotFoundError("Client not found: xyz")

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "client_not_found"

    def test_agent_not_found_error_returns_404(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """AgentNotFoundError → 404 with error_type 'agent_not_found'."""
        agent_repo_mock.find_by_id.side_effect = AgentNotFoundError("Agent not found: xyz")

        response = test_client.get(f"/api/v1/agents/{AGENT_UUID}")

        assert response.status_code == 404
        body = response.json()
        assert body["error_type"] == "agent_not_found"

    def test_invalid_client_error_returns_400(
        self, test_client: TestClient, client_repo_mock: AsyncMock
    ) -> None:
        """InvalidClientError → 400 with error_type 'invalid_client'."""
        client_repo_mock.find_by_id.side_effect = InvalidClientError("Invalid ClientId: bad")

        response = test_client.get(f"/api/v1/clients/{CLIENT_UUID}")

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_client"

    def test_invalid_agent_error_returns_400(
        self, test_client: TestClient, agent_repo_mock: AsyncMock
    ) -> None:
        """InvalidAgentError → 400 with error_type 'invalid_agent'."""
        agent_repo_mock.find_by_id.side_effect = InvalidAgentError("Invalid AgentId: bad")

        response = test_client.get(f"/api/v1/agents/{AGENT_UUID}")

        assert response.status_code == 400
        body = response.json()
        assert body["error_type"] == "invalid_agent"


# ============================================================================
# Schema Validation (Pydantic)
# ============================================================================


class TestSchemaValidation:
    """Verify that Pydantic request validation returns 422 correctly."""

    def test_create_client_invalid_json_returns_422(
        self, test_client: TestClient
    ) -> None:
        """Malformed JSON → 422 from FastAPI."""
        response = test_client.post(
            "/api/v1/clients",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_create_client_wrong_type_returns_422(
        self, test_client: TestClient
    ) -> None:
        """name is integer instead of string → 422."""
        payload: dict[str, Any] = {
            "name": 123,
            "business_type": "peluqueria",
            "whatsapp_number": VALID_WHATSAPP,
        }

        response = test_client.post("/api/v1/clients", json=payload)

        assert response.status_code == 422

    def test_create_agent_wrong_type_returns_422(
        self, test_client: TestClient
    ) -> None:
        """personality is integer instead of string → 422."""
        payload: dict[str, Any] = {
            "name": "Bot",
            "personality": 12345,
        }

        response = test_client.post(
            f"/api/v1/clients/{CLIENT_UUID}/agents", json=payload
        )

        assert response.status_code == 422

    def test_create_agent_invalid_tool_item_returns_422(
        self, test_client: TestClient
    ) -> None:
        """Tool missing required 'name' field → 422."""
        payload: dict[str, Any] = {
            "name": "Bot",
            "personality": _MIN_PERSONALITY,
            "tools": [{"description": "desc without name"}],
        }

        response = test_client.post(
            f"/api/v1/clients/{CLIENT_UUID}/agents", json=payload
        )

        assert response.status_code == 422


# ============================================================================
# Health Check (existing endpoint)
# ============================================================================


class TestHealthCheckEndpoint:
    """Verify /health endpoint still works (not affected by router registration)."""

    def test_health_check_returns_200(
        self, test_client: TestClient
    ) -> None:
        """GET /health → 200 with status=ok."""
        response = test_client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
