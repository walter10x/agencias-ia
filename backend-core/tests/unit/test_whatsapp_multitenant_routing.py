"""Unit tests del routing multi-tenant del webhook de Meta (Fase 3, tarea 3.3).

Cubre:
- MetaMetadata/MetaValue exponen phone_number_id del payload.
- process_whatsapp_message resuelve el cliente por phone_number_id
  cuando se provee, con fallback a find_by_whatsapp si no hay match.
- Dos tenants con distinto phone_number_id reciben cada uno su propio
  cliente/agente (aislamiento).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber
from app.infrastructure.whatsapp.message_processor import process_whatsapp_message
from app.infrastructure.whatsapp.schemas import MetaMetadata, MetaValue

TENANT_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _make_client(client_id: uuid.UUID, whatsapp_number: str) -> Client:
    c = Client(
        name=f"Negocio {client_id}",
        business_type=BusinessType("otro"),
        whatsapp_number=WhatsAppNumber(whatsapp_number),
    )
    object.__setattr__(c, "id", client_id)
    object.__setattr__(c, "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    object.__setattr__(c, "updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    c.phone_number_id = f"pnid-{client_id}"
    return c


def _make_agent(client_id: uuid.UUID) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        client_id=ClientId(client_id),
        name="Agente",
        personality="Eres un asistente amable y profesional. Diez caracteres minimo.",
        tools=[AgentTool(name="t1", description="d1", endpoint="https://n8n.example.com/t1")],
        knowledge_base_refs=[],
        is_active=True,
    )


class TestMetaMetadataSchema:
    def test_meta_value_exposes_phone_number_id(self) -> None:
        value = MetaValue.model_validate(
            {
                "messages": [],
                "contacts": [],
                "metadata": {"display_phone_number": "1555000111", "phone_number_id": "1234567890"},
            }
        )
        assert value.metadata.phone_number_id == "1234567890"

    def test_meta_value_defaults_metadata_when_absent(self) -> None:
        value = MetaValue.model_validate({"messages": [], "contacts": []})
        assert isinstance(value.metadata, MetaMetadata)
        assert value.metadata.phone_number_id == ""


class TestProcessWhatsappMessageRouting:
    @pytest.fixture
    def client_repo(self) -> AsyncMock:
        return AsyncMock(spec=ClientRepository)

    @pytest.fixture
    def agent_repo(self) -> AsyncMock:
        return AsyncMock(spec=AgentRepository)

    @pytest.mark.asyncio
    async def test_resolves_tenant_by_phone_number_id_when_provided(
        self, client_repo: AsyncMock, agent_repo: AsyncMock
    ) -> None:
        client_a = _make_client(TENANT_A_ID, "573001111111")
        client_repo.find_by_phone_number_id.return_value = client_a
        agent_repo.find_active_by_client.return_value = [_make_agent(TENANT_A_ID)]

        with patch("app.infrastructure.whatsapp.message_processor.celery_app") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-1"
            mock_celery.send_task.return_value = mock_task

            result = await process_whatsapp_message(
                phone="573009999999",
                text="Hola",
                client_repo=client_repo,
                agent_repo=agent_repo,
                phone_number_id="pnid-tenant-a",
            )

        assert result.status == "queued"
        client_repo.find_by_phone_number_id.assert_awaited_once_with("pnid-tenant-a")
        # No debería recurrir al fallback por whatsapp si ya encontró por phone_number_id
        client_repo.find_by_whatsapp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_two_tenants_route_to_their_own_client_and_agents(
        self, client_repo: AsyncMock, agent_repo: AsyncMock
    ) -> None:
        """Aislamiento: dos phone_number_id distintos deben resolver clientes distintos."""
        client_a = _make_client(TENANT_A_ID, "573001111111")
        client_b = _make_client(TENANT_B_ID, "573002222222")

        async def fake_find_by_phone_number_id(pnid: str):
            return {"pnid-a": client_a, "pnid-b": client_b}.get(pnid)

        client_repo.find_by_phone_number_id.side_effect = fake_find_by_phone_number_id
        agent_repo.find_active_by_client.side_effect = lambda client_id: [
            _make_agent(client_id.value if hasattr(client_id, "value") else client_id)
        ]

        with patch("app.infrastructure.whatsapp.message_processor.celery_app") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-a"
            mock_celery.send_task.return_value = mock_task

            result_a = await process_whatsapp_message(
                phone="573005550001",
                text="Hola desde A",
                client_repo=client_repo,
                agent_repo=agent_repo,
                phone_number_id="pnid-a",
            )
            call_kwargs_a = mock_celery.send_task.call_args.kwargs

        with patch("app.infrastructure.whatsapp.message_processor.celery_app") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-b"
            mock_celery.send_task.return_value = mock_task

            result_b = await process_whatsapp_message(
                phone="573005550002",
                text="Hola desde B",
                client_repo=client_repo,
                agent_repo=agent_repo,
                phone_number_id="pnid-b",
            )
            call_kwargs_b = mock_celery.send_task.call_args.kwargs

        assert result_a.status == "queued"
        assert result_b.status == "queued"
        assert call_kwargs_a["kwargs"]["client_id"] == str(TENANT_A_ID)
        assert call_kwargs_b["kwargs"]["client_id"] == str(TENANT_B_ID)
        assert call_kwargs_a["kwargs"]["client_id"] != call_kwargs_b["kwargs"]["client_id"]

    @pytest.mark.asyncio
    async def test_falls_back_to_whatsapp_lookup_when_phone_number_id_not_found(
        self, client_repo: AsyncMock, agent_repo: AsyncMock
    ) -> None:
        """Si no hay match por phone_number_id, se usa el lookup previo (Evolution/legacy)."""
        client_repo.find_by_phone_number_id.return_value = None
        client_legacy = _make_client(TENANT_A_ID, "573003333333")
        client_repo.find_by_whatsapp.return_value = client_legacy
        agent_repo.find_active_by_client.return_value = [_make_agent(TENANT_A_ID)]

        with patch("app.infrastructure.whatsapp.message_processor.celery_app") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-fallback"
            mock_celery.send_task.return_value = mock_task

            result = await process_whatsapp_message(
                phone="573003333333",
                text="Hola",
                client_repo=client_repo,
                agent_repo=agent_repo,
                phone_number_id="unknown-pnid",
            )

        assert result.status == "queued"
        client_repo.find_by_phone_number_id.assert_awaited_once_with("unknown-pnid")
        client_repo.find_by_whatsapp.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_phone_number_id_skips_lookup_by_pnid(
        self, client_repo: AsyncMock, agent_repo: AsyncMock
    ) -> None:
        """Sin phone_number_id (Evolution API) — comportamiento previo intacto."""
        client_legacy = _make_client(TENANT_A_ID, "573003333333")
        client_repo.find_by_whatsapp.return_value = client_legacy
        agent_repo.find_active_by_client.return_value = [_make_agent(TENANT_A_ID)]

        with patch("app.infrastructure.whatsapp.message_processor.celery_app") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-legacy"
            mock_celery.send_task.return_value = mock_task

            result = await process_whatsapp_message(
                phone="573003333333",
                text="Hola",
                client_repo=client_repo,
                agent_repo=agent_repo,
            )

        assert result.status == "queued"
        client_repo.find_by_phone_number_id.assert_not_awaited()
        client_repo.find_by_whatsapp.assert_awaited_once_with("573003333333")
