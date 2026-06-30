"""Unit tests for SupabaseAgentRepository — fully mocked, no real Supabase needed."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.domain.agent.entity import Agent, AgentTool
from app.domain.shared.errors import AgentNotFoundError, InvalidAgentError
from app.domain.shared.value_objects import AgentId, ClientId
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository


def _make_mock_chain() -> MagicMock:
    """Create a mock that returns itself for all chained method calls."""
    chain = MagicMock()
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.offset.return_value = chain
    chain.execute.return_value = chain
    return chain


def _make_agent_row(
    id_: str,
    client_id: str = "11111111-1111-1111-1111-111111111111",
    name: str = "Bot",
    personality: str = "Ten chars min personality here.",
    tools: list[dict] | None = None,
    knowledge_base_refs: list[str] | None = None,
    is_active: bool = True,
) -> dict:
    return {
        "id": id_,
        "client_id": client_id,
        "name": name,
        "personality": personality,
        "tools": tools or [],
        "knowledge_base_refs": knowledge_base_refs or [],
        "is_active": is_active,
        "created_at": "2026-06-07T00:00:00+00:00",
        "updated_at": "2026-06-07T00:00:00+00:00",
    }


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    table = MagicMock()
    chain = _make_mock_chain()
    table.select.return_value = chain
    table.upsert.return_value = chain
    table.delete.return_value = chain
    db.table.return_value = table
    db._chain = chain
    db._table = table
    return db


@pytest.fixture
def repo(mock_db: MagicMock) -> SupabaseAgentRepository:
    return SupabaseAgentRepository(mock_db)


@pytest.fixture
def agent() -> Agent:
    return Agent(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        client_id=ClientId(UUID("11111111-1111-1111-1111-111111111111")),
        name="Bot Test",
        personality="Eres un asistente de prueba. Diez caracteres minimo.",
        tools=[AgentTool(name="t1", description="d1", endpoint="https://n8n.example.com/t1")],
        knowledge_base_refs=["kb-1", "kb-2"],
        is_active=True,
    )


# ======================================================================
# save()
# ======================================================================

@pytest.mark.asyncio
async def test_save_new_agent(repo: SupabaseAgentRepository, mock_db: MagicMock, agent: Agent) -> None:
    await repo.save(agent)
    mock_db._table.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_save_with_tools_serializes_to_jsonb(repo: SupabaseAgentRepository, mock_db: MagicMock, agent: Agent) -> None:
    await repo.save(agent)

    call_args = mock_db._table.upsert.call_args
    row = call_args[0][0]
    assert "tools" in row
    assert row["tools"] == [{"name": "t1", "description": "d1", "endpoint": "https://n8n.example.com/t1"}]


# ======================================================================
# find_by_id()
# ======================================================================

@pytest.mark.asyncio
async def test_find_by_id_returns_agent_with_tools(repo: SupabaseAgentRepository, mock_db: MagicMock, agent: Agent) -> None:
    mock_db._chain.data = [
        _make_agent_row(
            str(agent.id),
            name=agent.name,
            personality=agent.personality,
            tools=[{"name": "t1", "description": "d1", "endpoint": "https://n8n.example.com/t1"}],
            knowledge_base_refs=["kb-1", "kb-2"],
        )
    ]

    found = await repo.find_by_id(AgentId(value=agent.id))

    assert found is not None
    assert found.id == agent.id
    assert found.client_id == agent.client_id
    assert found.name == agent.name
    assert found.personality == agent.personality
    assert len(found.tools) == 1
    assert found.tools[0].name == "t1"
    assert found.tools[0].description == "d1"
    assert found.tools[0].endpoint == "https://n8n.example.com/t1"
    assert found.knowledge_base_refs == ["kb-1", "kb-2"]
    assert found.is_active is True


@pytest.mark.asyncio
async def test_find_by_id_returns_none_for_missing(repo: SupabaseAgentRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = []
    found = await repo.find_by_id(AgentId.generate())
    assert found is None


@pytest.mark.asyncio
async def test_find_by_id_deserializes_empty_tools(repo: SupabaseAgentRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = [
        _make_agent_row(str(uuid4()), tools=[], knowledge_base_refs=[])
    ]

    found = await repo.find_by_id(AgentId.generate())
    assert found is not None
    assert found.tools == []
    assert found.knowledge_base_refs == []


# ======================================================================
# find_active_by_client()
# ======================================================================

@pytest.mark.asyncio
async def test_find_active_by_client_returns_agents(repo: SupabaseAgentRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = [
        _make_agent_row(str(uuid4()), name="ActiveBot", is_active=True),
    ]

    result = await repo.find_active_by_client(ClientId(UUID("11111111-1111-1111-1111-111111111111")))

    assert len(result) == 1
    assert result[0].name == "ActiveBot"
    assert result[0].is_active


@pytest.mark.asyncio
async def test_find_active_by_client_returns_empty(repo: SupabaseAgentRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = []
    result = await repo.find_active_by_client(ClientId.generate())
    assert result == []


# ======================================================================
# delete()
# ======================================================================

@pytest.mark.asyncio
async def test_delete_existing_agent(repo: SupabaseAgentRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = [{"id": "22222222-2222-2222-2222-222222222222"}]

    await repo.delete(AgentId(UUID("22222222-2222-2222-2222-222222222222")))

    mock_db._table.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_nonexistent_agent_raises(repo: SupabaseAgentRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = []

    with pytest.raises(AgentNotFoundError):
        await repo.delete(AgentId.generate())


# ======================================================================
# Error mapping
# ======================================================================

@pytest.mark.asyncio
async def test_save_fk_violation_maps_to_invalid_agent(repo: SupabaseAgentRepository, mock_db: MagicMock, agent: Agent) -> None:
    """Simulate PostgreSQL 23503 foreign_key_violation."""
    error = Exception("insert or update violates foreign key constraint")
    error.code = "23503"  # type: ignore[attr-defined]
    mock_db._table.upsert.side_effect = error

    with pytest.raises(InvalidAgentError):
        await repo.save(agent)
