"""Integration tests for SupabaseAgentRepository.

These tests hit a real Supabase instance.  They are the RED phase of TDD:
the repository does NOT exist yet, so every test will fail on import.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.agent.entity import Agent, AgentTool
from app.domain.client.entity import Client
from app.domain.shared.errors import AgentNotFoundError, InvalidAgentError
from app.domain.shared.value_objects import (
    AgentId,
    BusinessType,
    ClientId,
    WhatsAppNumber,
)
from app.infrastructure.persistence.agent_repository import (  # type: ignore[import-untyped]  # noqa: E501
    SupabaseAgentRepository,
)
from app.infrastructure.persistence.client_repository import (  # type: ignore[import-untyped]  # noqa: E501
    SupabaseClientRepository,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ======================================================================
# Helpers
# ======================================================================

def _make_client_for_agent(
    name: str = "Agent Parent Client",
    whatsapp: str = "573009999001",
) -> Client:
    """Create a minimal Client to use as the parent of an Agent."""
    return Client(
        id=uuid4(),
        name=name,
        business_type=BusinessType("peluqueria"),
        whatsapp_number=WhatsAppNumber(whatsapp),
    )


def _make_agent(
    client_id: ClientId,
    *,
    name: str = "Test Agent",
    personality: str = "Eres un asistente amable. Respondes siempre con cortesia "
    "y das informacion precisa sobre el negocio.",
    active: bool = True,
    agent_id: UUID | None = None,
    tools: list[AgentTool] | None = None,
) -> Agent:
    """Shorthand factory for creating Agent entities in tests."""
    return Agent(
        id=agent_id or uuid4(),
        client_id=client_id,
        name=name,
        personality=personality,
        tools=tools or [],
        is_active=active,
    )


# ======================================================================
# save()
# ======================================================================

class TestSaveNewAgent:
    """RF-05: INSERT a brand-new agent (with tools JSONB)."""

    async def test_save_new_agent(
        self,
        client_repo: SupabaseClientRepository,
        agent_repo: SupabaseAgentRepository,
        sample_client: Client,
        sample_agent: Agent,
    ) -> None:
        """Saving a new agent with tools persists it correctly."""
        # Parent client must exist first (FK constraint)
        await client_repo.save(sample_client)

        await agent_repo.save(sample_agent)

        found = await agent_repo.find_by_id(AgentId(value=sample_agent.id))
        assert found is not None
        assert found.id == sample_agent.id
        assert found.name == sample_agent.name
        assert found.personality == sample_agent.personality
        assert len(found.tools) == 2
        assert found.tools[0].name == "agendar_cita"
        assert found.tools[1].name == "consultar_precios"
        assert found.is_active is True


class TestSaveExistingAgentUpdates:
    """RF-05: UPDATE an existing agent (UPSERT semantics)."""

    async def test_save_existing_agent_updates(
        self,
        client_repo: SupabaseClientRepository,
        agent_repo: SupabaseAgentRepository,
        sample_client: Client,
        sample_agent: Agent,
    ) -> None:
        """Saving an agent that already exists updates its fields."""
        await client_repo.save(sample_client)
        await agent_repo.save(sample_agent)

        # Modify in-memory
        sample_agent.update_personality(
            "Eres un asistente muy formal y profesional. "
            "Respondes de manera concisa, sin rodeos ni preguntas innecesarias."
        )
        sample_agent.add_tool(
            AgentTool(
                name="cancelar_cita",
                description="Cancela una cita previamente agendada",
                endpoint="https://n8n.example.com/webhook/cancelar",
            )
        )

        await agent_repo.save(sample_agent)

        found = await agent_repo.find_by_id(AgentId(value=sample_agent.id))
        assert found is not None
        assert "formal y profesional" in found.personality
        assert len(found.tools) == 3
        tool_names = {t.name for t in found.tools}
        assert "cancelar_cita" in tool_names


class TestSaveAgentWithInvalidClientIdRaises:
    """EC-06 / RF-05: FK violation → InvalidAgentError."""

    async def test_save_agent_with_invalid_client_id_raises(
        self,
        agent_repo: SupabaseAgentRepository,
    ) -> None:
        """Saving an agent whose client_id does not exist raises InvalidAgentError."""
        bad_client_id = ClientId.generate()
        agent = Agent(
            name="Orphan Agent",
            client_id=bad_client_id,
            personality="Eres un asistente solitario sin cliente padre. "
            "No deberias existir en la base de datos.",
        )

        with pytest.raises(InvalidAgentError):
            await agent_repo.save(agent)


# ======================================================================
# find_by_id()
# ======================================================================

class TestFindByIdReturnsAgentWithTools:
    """RF-06: retrieve an agent by its AgentId, including deserialized tools."""

    async def test_find_by_id_returns_agent_with_tools(
        self,
        client_repo: SupabaseClientRepository,
        agent_repo: SupabaseAgentRepository,
        sample_client: Client,
        sample_agent: Agent,
    ) -> None:
        """find_by_id returns the agent with all tools properly deserialized."""
        await client_repo.save(sample_client)
        await agent_repo.save(sample_agent)

        found = await agent_repo.find_by_id(AgentId(value=sample_agent.id))

        assert found is not None
        assert found.id == sample_agent.id
        assert found.name == sample_agent.name
        assert found.client_id == sample_agent.client_id
        assert found.personality == sample_agent.personality
        assert found.is_active == sample_agent.is_active

        # Tools deserialized correctly
        assert len(found.tools) == len(sample_agent.tools)
        for original, deserialized in zip(sample_agent.tools, found.tools):
            assert deserialized.name == original.name
            assert deserialized.description == original.description
            assert deserialized.endpoint == original.endpoint

        # knowledge_base_refs
        assert found.knowledge_base_refs == sample_agent.knowledge_base_refs


class TestFindByIdReturnsNoneForMissing:
    """EC-07 variant: valid UUID but agent does not exist → None."""

    async def test_find_by_id_returns_none_for_missing(
        self,
        agent_repo: SupabaseAgentRepository,
    ) -> None:
        """find_by_id with a random, unpersisted AgentId returns None."""
        random_id = AgentId.generate()
        found = await agent_repo.find_by_id(random_id)
        assert found is None


# ======================================================================
# find_active_by_client()
# ======================================================================

class TestFindActiveByClientReturnsOnlyActive:
    """RF-07: only active agents for a given client are returned."""

    async def test_find_active_by_client_returns_only_active(
        self,
        client_repo: SupabaseClientRepository,
        agent_repo: SupabaseAgentRepository,
        sample_client: Client,
        sample_agent: Agent,
    ) -> None:
        """find_active_by_client excludes inactive agents."""
        await client_repo.save(sample_client)

        inactive_agent = Agent(
            id=uuid4(),
            client_id=ClientId(value=sample_client.id),
            name="Inactive Agent",
            personality="Eres un asistente inactivo. Diez caracteres minimos.",
            is_active=False,
        )

        await agent_repo.save(sample_agent)  # active
        await agent_repo.save(inactive_agent)  # inactive

        cid = ClientId(value=sample_client.id)
        result = await agent_repo.find_active_by_client(cid)

        assert len(result) == 1
        assert result[0].id == sample_agent.id
        assert all(a.is_active for a in result)


class TestFindActiveByClientNoAgentsReturnsEmpty:
    """RF-07: client with no agents → empty list."""

    async def test_find_active_by_client_no_agents_returns_empty(
        self,
        client_repo: SupabaseClientRepository,
        agent_repo: SupabaseAgentRepository,
        sample_client: Client,
    ) -> None:
        """find_active_by_client returns [] when the client has no agents."""
        await client_repo.save(sample_client)

        cid = ClientId(value=sample_client.id)
        result = await agent_repo.find_active_by_client(cid)

        assert result == []
        assert isinstance(result, list)


# ======================================================================
# delete()
# ======================================================================

class TestDeleteExistingAgent:
    """RF-08: DELETE an existing agent successfully."""

    async def test_delete_existing_agent(
        self,
        client_repo: SupabaseClientRepository,
        agent_repo: SupabaseAgentRepository,
        sample_client: Client,
        sample_agent: Agent,
    ) -> None:
        """After deleting an agent, find_by_id returns None."""
        await client_repo.save(sample_client)
        await agent_repo.save(sample_agent)

        await agent_repo.delete(AgentId(value=sample_agent.id))

        # Post-delete consistency (EC-08)
        found = await agent_repo.find_by_id(AgentId(value=sample_agent.id))
        assert found is None


class TestDeleteNonexistentAgentRaises:
    """EC-07 / RF-08: deleting a non-existent agent → AgentNotFoundError."""

    async def test_delete_nonexistent_agent_raises(
        self,
        agent_repo: SupabaseAgentRepository,
    ) -> None:
        """Deleting an agent that was never saved raises AgentNotFoundError."""
        random_id = AgentId.generate()

        with pytest.raises(AgentNotFoundError):
            await agent_repo.delete(random_id)
