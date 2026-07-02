"""Tests: tenant isolation — client_id viene del JWT, no del body/query."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.dtos import CurrentClientOutput
from app.domain.agent.entity import Agent, AgentTool
from app.domain.shared.value_objects import ClientId
from app.infrastructure.http.agent_router import router as agent_router
from app.infrastructure.http.conversation_router import router as conversation_router
from app.infrastructure.http.email_router import router as email_router
from app.infrastructure.http.feedback_router import router as feedback_router
from app.infrastructure.http.lead_router import router as lead_router
from app.infrastructure.http.dependencies import (
    get_agent_repo,
    get_conversation_repo,
    get_current_client,
    get_email_repo,
    get_feedback_repo,
    get_lead_repo,
)
from app.infrastructure.http.error_handlers import register_error_handlers

CLIENT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CLIENT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
AGENT_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")

_MIN_PERSONALITY = "Eres un asistente amable y profesional. Diez caracteres minimo."


def _make_agent(**overrides) -> Agent:
    a = Agent(
        id=overrides.get("id", AGENT_UUID),
        client_id=overrides.get("client_id", ClientId(uuid.UUID(CLIENT_A))),
        name=str(overrides.get("name", "Test Agent")),
        personality=str(overrides.get("personality", _MIN_PERSONALITY)),
        tools=overrides.get("tools", [AgentTool(name="t1", description="d1", endpoint="https://n8n.example.com/t1")]),
        knowledge_base_refs=overrides.get("knowledge_base_refs", ["kb-1"]),
        is_active=bool(overrides.get("is_active", True)),
    )
    return a


@pytest.fixture
def lead_repo() -> AsyncMock:
    m = AsyncMock()
    m.find_by_client_and_phone.return_value = None
    m.list_by_client.return_value = []
    m.count_by_client.return_value = 0
    return m


@pytest.fixture
def conversation_repo() -> AsyncMock:
    m = AsyncMock()
    m.list_by_client.return_value = ([], 0)
    return m


@pytest.fixture
def agent_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def email_repo() -> AsyncMock:
    m = AsyncMock()
    m.list_by_client.return_value = []
    return m


@pytest.fixture
def feedback_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def current_client() -> CurrentClientOutput:
    return CurrentClientOutput(
        client_id=CLIENT_A,
        email="client_a@test.com",
        name="Client A",
        role="client",
        status="approved",
        is_active=True,
        whatsapp_number="573001234567",
        whatsapp_connected=True,
        plan="free",
    )


@pytest.fixture
def app(
    lead_repo: AsyncMock,
    conversation_repo: AsyncMock,
    agent_repo: AsyncMock,
    email_repo: AsyncMock,
    feedback_repo: AsyncMock,
    current_client: CurrentClientOutput,
) -> FastAPI:
    test_app = FastAPI(title="Tenant Isolation Test")
    register_error_handlers(test_app)
    test_app.include_router(lead_router, prefix="/api/v1/leads", tags=["Leads"])
    test_app.include_router(conversation_router, prefix="/api/v1/conversations", tags=["Conversations"])
    test_app.include_router(agent_router, prefix="/api/v1/agents", tags=["Agents"])
    test_app.include_router(email_router, prefix="/api/v1/emails", tags=["Emails"])
    test_app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])

    test_app.dependency_overrides[get_lead_repo] = lambda: lead_repo
    test_app.dependency_overrides[get_conversation_repo] = lambda: conversation_repo
    test_app.dependency_overrides[get_agent_repo] = lambda: agent_repo
    test_app.dependency_overrides[get_email_repo] = lambda: email_repo
    test_app.dependency_overrides[get_feedback_repo] = lambda: feedback_repo
    test_app.dependency_overrides[get_current_client] = lambda: current_client
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ===========================================================================
# Lead Router
# ===========================================================================

class TestLeadTenantIsolation:
    def test_create_lead_overrides_client_id_from_jwt(
        self, client: TestClient, lead_repo: AsyncMock
    ) -> None:
        resp = client.post("/api/v1/leads", json={
            "client_id": CLIENT_B,
            "phone": "573001234567",
            "name": "Lead A",
            "source": "landing",
        })

        assert resp.status_code == 201
        lead_repo.find_by_client_and_phone.assert_called_once()
        assert lead_repo.find_by_client_and_phone.call_args[1]["client_id"] == CLIENT_A

    def test_list_leads_filters_by_jwt_client_id(
        self, client: TestClient, lead_repo: AsyncMock
    ) -> None:
        resp = client.get("/api/v1/leads")

        assert resp.status_code == 200
        lead_repo.list_by_client.assert_called_once()
        assert lead_repo.list_by_client.call_args[1]["client_id"] == CLIENT_A
        lead_repo.count_by_client.assert_called_once()
        assert lead_repo.count_by_client.call_args[1]["client_id"] == CLIENT_A


# ===========================================================================
# Conversation Router
# ===========================================================================

class TestConversationTenantIsolation:
    def test_list_conversations_filters_by_jwt_client_id(self, client: TestClient) -> None:
        with patch("app.infrastructure.http.conversation_router.ListConversationsUseCase") as mock_uc_cls:
            mock_uc = AsyncMock()
            mock_uc_cls.return_value = mock_uc
            mock_uc.execute.return_value = ([], 0)

            resp = client.get("/api/v1/conversations")

            assert resp.status_code == 200
            mock_uc.execute.assert_called_once()
            assert mock_uc.execute.call_args[0][0].client_id == CLIENT_A


# ===========================================================================
# Email Router
# ===========================================================================

class TestEmailTenantIsolation:
    def test_send_email_overrides_client_id_from_jwt(self, client: TestClient) -> None:
        with patch("app.infrastructure.http.email_router.SendEmailUseCase") as mock_uc_cls:
            mock_uc = AsyncMock()
            mock_uc_cls.return_value = mock_uc
            mock_uc.execute.return_value = {"id": "msg-1", "status": "sent"}

            resp = client.post("/api/v1/emails/send", json={
                "client_id": CLIENT_B,
                "to_email": "test@example.com",
                "rubro_slug": "inmobiliario",
                "sequence_number": 1,
                "lead_id": "11111111-1111-1111-1111-111111111111",
                "business_name": "Test",
                "contact_name": "Test",
            })

            assert resp.status_code == 201
            mock_uc.execute.assert_called_once()
            dto = mock_uc.execute.call_args[0][0]
            assert dto.client_id == CLIENT_A

    def test_list_emails_filters_by_jwt_client_id(
        self, client: TestClient, email_repo: AsyncMock
    ) -> None:
        resp = client.get("/api/v1/emails")

        assert resp.status_code == 200
        email_repo.list_by_client.assert_called_once()
        assert email_repo.list_by_client.call_args[1]["client_id"] == CLIENT_A


# ===========================================================================
# Feedback Router
# ===========================================================================

class TestFeedbackTenantIsolation:
    def test_create_feedback_overrides_client_id_from_jwt(self, client: TestClient) -> None:
        with patch("app.infrastructure.http.feedback_router.CreateFeedbackUseCase") as mock_uc_cls:
            mock_uc = AsyncMock()
            mock_uc_cls.return_value = mock_uc

            class FakeFeedbackOutput:
                id = "fb-1"
                client_id = CLIENT_A
                lead_id = "11111111-1111-1111-1111-111111111111"
                conversation_id = "11111111-1111-1111-1111-111111111111"
                rating = 5
                comment = "Great!"
                created_at = "2026-01-01T00:00:00Z"

            mock_uc.execute.return_value = FakeFeedbackOutput()

            resp = client.post("/api/v1/feedback", json={
                "client_id": CLIENT_B,
                "rating": 5,
                "lead_id": "11111111-1111-1111-1111-111111111111",
                "conversation_id": "11111111-1111-1111-1111-111111111111",
                "comment": "Great!",
            })

            assert resp.status_code == 201
            mock_uc.execute.assert_called_once()
            assert mock_uc.execute.call_args[0][0].client_id == CLIENT_A

    def test_list_feedback_filters_by_jwt_client_id(self, client: TestClient) -> None:
        with patch("app.infrastructure.http.feedback_router.ListFeedbackUseCase") as mock_uc_cls:
            mock_uc = AsyncMock()
            mock_uc_cls.return_value = mock_uc
            mock_uc.execute.return_value = ([], 0)

            resp = client.get("/api/v1/feedback")

            assert resp.status_code == 200
            mock_uc.execute.assert_called_once()
            assert mock_uc.execute.call_args[0][0].client_id == CLIENT_A


# ===========================================================================
# Agent Router — cross-tenant access control
# ===========================================================================

class TestAgentCrossTenant:
    def test_get_agent_from_other_tenant_returns_403(
        self, client: TestClient, agent_repo: AsyncMock
    ) -> None:
        other_agent = _make_agent(client_id=ClientId(uuid.UUID(CLIENT_B)))
        agent_repo.find_by_id.return_value = other_agent

        resp = client.get(f"/api/v1/agents/{AGENT_UUID}")

        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] == "forbidden"

    def test_update_agent_from_other_tenant_returns_403(
        self, client: TestClient, agent_repo: AsyncMock
    ) -> None:
        other_agent = _make_agent(client_id=ClientId(uuid.UUID(CLIENT_B)))
        agent_repo.find_by_id.return_value = other_agent

        resp = client.patch(f"/api/v1/agents/{AGENT_UUID}", json={"name": "Hacked Name"})

        assert resp.status_code == 403

    def test_deactivate_agent_from_other_tenant_returns_403(
        self, client: TestClient, agent_repo: AsyncMock
    ) -> None:
        other_agent = _make_agent(client_id=ClientId(uuid.UUID(CLIENT_B)))
        agent_repo.find_by_id.return_value = other_agent

        resp = client.delete(f"/api/v1/agents/{AGENT_UUID}")

        assert resp.status_code == 403

    def test_delete_agent_from_other_tenant_returns_403(
        self, client: TestClient, agent_repo: AsyncMock
    ) -> None:
        other_agent = _make_agent(client_id=ClientId(uuid.UUID(CLIENT_B)))
        agent_repo.find_by_id.return_value = other_agent

        resp = client.delete(f"/api/v1/agents/{AGENT_UUID}/permanent")

        assert resp.status_code == 403
