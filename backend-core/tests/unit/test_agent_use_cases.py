"""Unit tests for Agent application use cases (RED phase — TDD).

These tests import use case classes and DTOs that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: CreateAgent, GetAgent, ListAgentsByClient, UpdateAgent,
          DeactivateAgent, DeleteAgent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.agent.create_agent import CreateAgentUseCase
from app.application.agent.deactivate_agent import DeactivateAgentUseCase
from app.application.agent.delete_agent import DeleteAgentUseCase
from app.application.agent.get_agent import GetAgentUseCase
from app.application.agent.list_agents import ListAgentsByClientUseCase
from app.application.agent.update_agent import UpdateAgentUseCase
from app.application.dtos import (
    AgentOutput,
    AgentToolInput,
    AgentToolOutput,
    CreateAgentInput,
    DeactivateAgentInput,
    DeleteAgentInput,
    GetAgentInput,
    ListAgentsByClientInput,
    UpdateAgentInput,
)

# --- Domain layer (already exists) ---
from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import (
    AgentNotFoundError,
    DomainError,
    InvalidAgentError,
    InvalidClientError,
)
from app.domain.shared.value_objects import AgentId, BusinessType, ClientId, WhatsAppNumber


# ============================================================================
# Helpers
# ============================================================================

CLIENT_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AGENT_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")

_MIN_PERSONALITY = "Eres un asistente amable y profesional. Diez caracteres minimo."


def _make_client(**overrides: object) -> Client:
    """Factory for Client entities used only for existence checks."""
    c = Client(
        name=str(overrides.get("name", "Test Client")),
        business_type=overrides.get("business_type", BusinessType("otro")),  # type: ignore[arg-type]
        whatsapp_number=overrides.get("whatsapp_number", WhatsAppNumber("573001234567")),  # type: ignore[arg-type]
    )
    if "id" in overrides:
        object.__setattr__(c, "id", overrides["id"])
    else:
        object.__setattr__(c, "id", CLIENT_UUID)
    object.__setattr__(c, "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    object.__setattr__(c, "updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    return c


def _make_agent(**overrides: object) -> Agent:
    """Factory for Agent entities with overridable fields.

    Creates a valid Agent with minimum personality (10+ chars) and
    default tools/knowledge_base_refs. Timestamps default to 2026-01-01 UTC.
    """
    a = Agent(
        id=overrides.get("id", uuid.uuid4()),  # type: ignore[arg-type]
        client_id=overrides.get("client_id", ClientId(CLIENT_UUID)),  # type: ignore[arg-type]
        name=str(overrides.get("name", "Test Agent")),
        personality=str(overrides.get("personality", _MIN_PERSONALITY)),
        tools=overrides.get("tools", [AgentTool(name="t1", description="d1", endpoint="https://n8n.example.com/t1")]),  # type: ignore[arg-type]
        knowledge_base_refs=overrides.get("knowledge_base_refs", ["kb-1"]),  # type: ignore[arg-type]
        is_active=bool(overrides.get("is_active", True)),
    )
    if "created_at" in overrides:
        object.__setattr__(a, "created_at", overrides["created_at"])
    else:
        object.__setattr__(a, "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    if "updated_at" in overrides:
        object.__setattr__(a, "updated_at", overrides["updated_at"])
    else:
        object.__setattr__(a, "updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    return a


def _tools_to_input(tools: list[AgentTool]) -> list[AgentToolInput]:
    """Convert AgentTool entities back to AgentToolInput DTOs for test assertions."""
    return [
        AgentToolInput(name=t.name, description=t.description, endpoint=t.endpoint)
        for t in tools
    ]


# ============================================================================
# CreateAgentUseCase  (RF-09, RF-10)
# ============================================================================

class TestCreateAgentUseCase:
    """RF-09 (happy), RF-10 (client not found), EC-17–EC-20, EC-30."""

    @pytest.mark.asyncio
    async def test_creates_agent_successfully(self) -> None:
        """RF-09: valid input, client exists → AgentOutput, both repos called."""
        client = _make_client()
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_client_repo = AsyncMock(spec=ClientRepository)
        mock_client_repo.find_by_id.return_value = client

        uc = CreateAgentUseCase(mock_agent_repo, mock_client_repo)
        inp = CreateAgentInput(
            client_id=str(CLIENT_UUID),
            name="Bot de Agendamiento",
            personality=_MIN_PERSONALITY,
            tools=[
                AgentToolInput(name="calendar", description="Consulta agenda", endpoint="https://n8n.example.com/cal"),
            ],
            knowledge_base_refs=["kb-precios"],
        )

        output = await uc.execute(inp)

        # Client repo used for existence check
        mock_client_repo.find_by_id.assert_awaited_once()
        # Agent repo used for persistence
        mock_agent_repo.save.assert_awaited_once()

        assert isinstance(output, AgentOutput)
        assert output.name == "Bot de Agendamiento"
        assert output.personality == _MIN_PERSONALITY
        assert output.client_id == str(CLIENT_UUID)
        assert output.is_active is True
        assert len(output.tools) == 1
        assert output.tools[0].name == "calendar"
        assert output.knowledge_base_refs == ["kb-precios"]

    @pytest.mark.asyncio
    async def test_raises_when_client_not_found(self) -> None:
        """RF-10 / EC-20: client_id does not exist → InvalidAgentError."""
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_client_repo = AsyncMock(spec=ClientRepository)
        mock_client_repo.find_by_id.return_value = None

        uc = CreateAgentUseCase(mock_agent_repo, mock_client_repo)
        inp = CreateAgentInput(
            client_id=str(CLIENT_UUID),
            name="Bot",
            personality=_MIN_PERSONALITY,
        )

        with pytest.raises(InvalidAgentError, match="Client not found"):
            await uc.execute(inp)

        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_personality_too_short(self) -> None:
        """EC-17: personality < 10 chars → ValueError from entity/use-case."""
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_client_repo = AsyncMock(spec=ClientRepository)
        mock_client_repo.find_by_id.return_value = _make_client()

        uc = CreateAgentUseCase(mock_agent_repo, mock_client_repo)
        inp = CreateAgentInput(
            client_id=str(CLIENT_UUID),
            name="Bot",
            personality="corto",  # only 5 chars
        )

        with pytest.raises(ValueError, match="at least 10 chars"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_creates_agent_with_empty_tools(self) -> None:
        """EC-18: tools=[] → success, agent created without tools."""
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_client_repo = AsyncMock(spec=ClientRepository)
        mock_client_repo.find_by_id.return_value = _make_client()

        uc = CreateAgentUseCase(mock_agent_repo, mock_client_repo)
        inp = CreateAgentInput(
            client_id=str(CLIENT_UUID),
            name="Minimal Bot",
            personality=_MIN_PERSONALITY,
            tools=[],
            knowledge_base_refs=[],
        )

        output = await uc.execute(inp)

        assert output.tools == []
        assert output.knowledge_base_refs == []
        mock_agent_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_on_empty_agent_name(self) -> None:
        """Empty agent name → InvalidAgentError or ValueError."""
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_client_repo = AsyncMock(spec=ClientRepository)
        mock_client_repo.find_by_id.return_value = _make_client()

        uc = CreateAgentUseCase(mock_agent_repo, mock_client_repo)
        inp = CreateAgentInput(
            client_id=str(CLIENT_UUID),
            name="",
            personality=_MIN_PERSONALITY,
        )

        with pytest.raises((InvalidAgentError, ValueError), match="empty"):
            await uc.execute(inp)

        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_client_id_format(self) -> None:
        """Non-UUID client_id → InvalidClientError from ClientId VO."""
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_client_repo = AsyncMock(spec=ClientRepository)

        uc = CreateAgentUseCase(mock_agent_repo, mock_client_repo)
        inp = CreateAgentInput(
            client_id="not-a-uuid",
            name="Bot",
            personality=_MIN_PERSONALITY,
        )

        with pytest.raises(InvalidClientError, match="Invalid ClientId"):
            await uc.execute(inp)


# ============================================================================
# GetAgentUseCase  (RF-11)
# ============================================================================

class TestGetAgentUseCase:
    """RF-11, EC-21."""

    @pytest.mark.asyncio
    async def test_finds_agent_successfully(self) -> None:
        """RF-11: existing agent_id → AgentOutput with all fields."""
        agent = _make_agent(id=AGENT_UUID, tools=[
            AgentTool(name="t1", description="desc", endpoint="https://n8n.example.com/t1"),
            AgentTool(name="t2", description="desc2", endpoint="https://n8n.example.com/t2"),
        ])
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = GetAgentUseCase(mock_repo)
        inp = GetAgentInput(agent_id=str(AGENT_UUID))

        output = await uc.execute(inp)

        assert output.id == str(AGENT_UUID)
        assert output.client_id == str(CLIENT_UUID)
        assert output.name == agent.name
        assert output.personality == agent.personality
        assert len(output.tools) == 2
        assert output.tools[0].name == "t1"
        assert output.tools[1].name == "t2"
        assert output.knowledge_base_refs == ["kb-1"]
        assert output.is_active is True
        mock_repo.find_by_id.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_agent_not_found(self) -> None:
        """EC-21: non-existent agent_id → AgentNotFoundError."""
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = None

        uc = GetAgentUseCase(mock_repo)
        inp = GetAgentInput(agent_id=str(AGENT_UUID))

        with pytest.raises(AgentNotFoundError, match="Agent not found"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_raises_on_invalid_agent_id(self) -> None:
        """Non-UUID agent_id → InvalidAgentError from AgentId VO."""
        mock_repo = AsyncMock(spec=AgentRepository)
        uc = GetAgentUseCase(mock_repo)
        inp = GetAgentInput(agent_id="not-a-uuid")

        with pytest.raises(InvalidAgentError, match="Invalid AgentId"):
            await uc.execute(inp)


# ============================================================================
# ListAgentsByClientUseCase  (RF-12)
# ============================================================================

class TestListAgentsByClientUseCase:
    """RF-12, EC-22, EC-23."""

    @pytest.mark.asyncio
    async def test_lists_agents_for_client(self) -> None:
        """RF-12: client has active agents → list[AgentOutput]."""
        agents = [
            _make_agent(id=uuid.uuid4(), name=f"Agent {i}") for i in range(2)
        ]
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_active_by_client.return_value = agents

        uc = ListAgentsByClientUseCase(mock_repo)
        inp = ListAgentsByClientInput(client_id=str(CLIENT_UUID))

        outputs = await uc.execute(inp)

        assert len(outputs) == 2
        assert all(isinstance(o, AgentOutput) for o in outputs)
        assert outputs[0].name == "Agent 0"
        assert outputs[1].name == "Agent 1"

        # Called with correct ClientId
        expected_cid = ClientId(CLIENT_UUID)
        mock_repo.find_active_by_client.assert_awaited_once_with(expected_cid)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_agents(self) -> None:
        """EC-22: client has no active agents → []."""
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_active_by_client.return_value = []

        uc = ListAgentsByClientUseCase(mock_repo)
        inp = ListAgentsByClientInput(client_id=str(CLIENT_UUID))

        outputs = await uc.execute(inp)

        assert outputs == []

    @pytest.mark.asyncio
    async def test_only_active_agents_returned(self) -> None:
        """EC-23: repository filters deactivated agents; use case maps what it gets."""
        active = _make_agent(id=uuid.uuid4(), name="ActiveOne", is_active=True)
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_active_by_client.return_value = [active]

        uc = ListAgentsByClientUseCase(mock_repo)
        inp = ListAgentsByClientInput(client_id=str(CLIENT_UUID))

        outputs = await uc.execute(inp)

        assert len(outputs) == 1
        assert outputs[0].is_active is True

    @pytest.mark.asyncio
    async def test_raises_on_invalid_client_id(self) -> None:
        """Non-UUID client_id → InvalidClientError from ClientId VO."""
        mock_repo = AsyncMock(spec=AgentRepository)
        uc = ListAgentsByClientUseCase(mock_repo)
        inp = ListAgentsByClientInput(client_id="not-a-uuid")

        with pytest.raises(InvalidClientError, match="Invalid ClientId"):
            await uc.execute(inp)


# ============================================================================
# UpdateAgentUseCase  (RF-13)
# ============================================================================

class TestUpdateAgentUseCase:
    """RF-13, EC-24, EC-25."""

    @pytest.mark.asyncio
    async def test_updates_personality_only(self) -> None:
        """Only personality provided → personality updated, others unchanged."""
        agent = _make_agent(id=AGENT_UUID, personality="Original prompt with 10+ chars.")
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = UpdateAgentUseCase(mock_repo)
        inp = UpdateAgentInput(
            agent_id=str(AGENT_UUID),
            personality="Nueva personalidad de mas de 10 caracteres!",
        )

        output = await uc.execute(inp)

        assert output.personality == "Nueva personalidad de mas de 10 caracteres!"
        assert output.name == "Test Agent"  # unchanged
        assert len(output.tools) == 1  # unchanged
        mock_repo.save.assert_awaited_once_with(agent)

    @pytest.mark.asyncio
    async def test_updates_tools_only(self) -> None:
        """EC-25: tools provided → old tools replaced entirely."""
        agent = _make_agent(id=AGENT_UUID, tools=[
            AgentTool(name="old_tool", description="old", endpoint="https://old.example.com"),
        ])
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = UpdateAgentUseCase(mock_repo)
        new_tools = [
            AgentToolInput(name="new_tool", description="new", endpoint="https://new.example.com"),
        ]
        inp = UpdateAgentInput(agent_id=str(AGENT_UUID), tools=new_tools)

        output = await uc.execute(inp)

        assert len(output.tools) == 1
        assert output.tools[0].name == "new_tool"
        assert output.tools[0].endpoint == "https://new.example.com"
        assert len(agent.tools) == 1
        mock_repo.save.assert_awaited_once_with(agent)

    @pytest.mark.asyncio
    async def test_updates_name_only(self) -> None:
        """Only name provided → name updated, validated not empty."""
        agent = _make_agent(id=AGENT_UUID, name="Old Name")
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = UpdateAgentUseCase(mock_repo)
        inp = UpdateAgentInput(agent_id=str(AGENT_UUID), name="New Agent Name")

        output = await uc.execute(inp)

        assert output.name == "New Agent Name"
        assert agent.name == "New Agent Name"
        mock_repo.save.assert_awaited_once_with(agent)

    @pytest.mark.asyncio
    async def test_updates_multiple_fields(self) -> None:
        """Multiple fields provided → all updated."""
        agent = _make_agent(
            id=AGENT_UUID,
            name="Old",
            personality="Old personality with 10 chars...",
            knowledge_base_refs=["old-kb"],
        )
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = UpdateAgentUseCase(mock_repo)
        inp = UpdateAgentInput(
            agent_id=str(AGENT_UUID),
            name="Updated Bot",
            personality="Updated personality count 10+ chars.",
            knowledge_base_refs=["new-kb-1", "new-kb-2"],
        )

        output = await uc.execute(inp)

        assert output.name == "Updated Bot"
        assert output.personality == "Updated personality count 10+ chars."
        assert output.knowledge_base_refs == ["new-kb-1", "new-kb-2"]
        mock_repo.save.assert_awaited_once_with(agent)

    @pytest.mark.asyncio
    async def test_raises_when_agent_not_found(self) -> None:
        """Non-existent agent_id → AgentNotFoundError."""
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = None

        uc = UpdateAgentUseCase(mock_repo)
        inp = UpdateAgentInput(
            agent_id=str(AGENT_UUID), name="New Name"
        )

        with pytest.raises(AgentNotFoundError):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_empty_name_update(self) -> None:
        """Empty name → validation error."""
        agent = _make_agent(id=AGENT_UUID)
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = UpdateAgentUseCase(mock_repo)
        inp = UpdateAgentInput(agent_id=str(AGENT_UUID), name="")

        with pytest.raises((InvalidAgentError, ValueError), match="empty"):
            await uc.execute(inp)


# ============================================================================
# DeactivateAgentUseCase  (RF-14)
# ============================================================================

class TestDeactivateAgentUseCase:
    """RF-14, EC-26."""

    @pytest.mark.asyncio
    async def test_deactivates_agent_successfully(self) -> None:
        """RF-14: active agent → deactivated, is_active=False in output."""
        agent = _make_agent(id=AGENT_UUID, is_active=True)
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = DeactivateAgentUseCase(mock_repo)
        inp = DeactivateAgentInput(agent_id=str(AGENT_UUID))

        output = await uc.execute(inp)

        assert output.is_active is False
        assert agent.is_active is False
        assert output.id == str(AGENT_UUID)
        mock_repo.save.assert_awaited_once_with(agent)

    @pytest.mark.asyncio
    async def test_raises_when_agent_not_found(self) -> None:
        """Non-existent agent_id → AgentNotFoundError."""
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = None

        uc = DeactivateAgentUseCase(mock_repo)
        inp = DeactivateAgentInput(agent_id=str(AGENT_UUID))

        with pytest.raises(AgentNotFoundError):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_deactivate_is_idempotent(self) -> None:
        """EC-26: already deactivated → still succeeds, is_active=False."""
        agent = _make_agent(id=AGENT_UUID, is_active=False)
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.find_by_id.return_value = agent

        uc = DeactivateAgentUseCase(mock_repo)
        inp = DeactivateAgentInput(agent_id=str(AGENT_UUID))

        output = await uc.execute(inp)

        assert output.is_active is False
        mock_repo.save.assert_awaited_once_with(agent)


# ============================================================================
# DeleteAgentUseCase  (RF-15)
# ============================================================================

class TestDeleteAgentUseCase:
    """RF-15, EC-27, EC-28."""

    @pytest.mark.asyncio
    async def test_deletes_agent_successfully(self) -> None:
        """RF-15: existing agent → delete called on repo, returns None."""
        mock_repo = AsyncMock(spec=AgentRepository)
        # delete() succeeds (no exception)

        uc = DeleteAgentUseCase(mock_repo)
        inp = DeleteAgentInput(agent_id=str(AGENT_UUID))

        result = await uc.execute(inp)

        assert result is None
        expected_aid = AgentId(AGENT_UUID)
        mock_repo.delete.assert_awaited_once_with(expected_aid)

    @pytest.mark.asyncio
    async def test_raises_when_agent_not_found(self) -> None:
        """EC-27: agent does not exist → AgentNotFoundError from repository."""
        mock_repo = AsyncMock(spec=AgentRepository)
        mock_repo.delete.side_effect = AgentNotFoundError(
            f"Agent not found: {AGENT_UUID}"
        )

        uc = DeleteAgentUseCase(mock_repo)
        inp = DeleteAgentInput(agent_id=str(AGENT_UUID))

        with pytest.raises(AgentNotFoundError):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_raises_on_invalid_agent_id(self) -> None:
        """Non-UUID agent_id → InvalidAgentError before repo call."""
        mock_repo = AsyncMock(spec=AgentRepository)
        uc = DeleteAgentUseCase(mock_repo)
        inp = DeleteAgentInput(agent_id="not-a-uuid")

        with pytest.raises(InvalidAgentError, match="Invalid AgentId"):
            await uc.execute(inp)

        mock_repo.delete.assert_not_awaited()


# ============================================================================
# Agent DTO validation  (post_init checks)
# ============================================================================

class TestAgentDTOValidation:
    """DTO __post_init__ guards — happen before use case execution."""

    def test_update_agent_input_requires_at_least_one_field(self) -> None:
        """EC-24: all fields None → ValueError on construction."""
        with pytest.raises(
            ValueError, match="Must provide at least one field to update"
        ):
            UpdateAgentInput(agent_id=str(AGENT_UUID))
