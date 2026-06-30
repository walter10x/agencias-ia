"""Caso de uso: desactivar un agente (soft delete)."""

from __future__ import annotations

from app.application.dtos import AgentOutput, DeactivateAgentInput, agent_to_output
from app.domain.agent.repository import AgentRepository
from app.domain.shared.errors import AgentNotFoundError
from app.domain.shared.value_objects import AgentId


class DeactivateAgentUseCase:
    """Orquesta la desactivación de un agente."""

    def __init__(self, agent_repo: AgentRepository) -> None:
        self._repo = agent_repo

    async def execute(self, input: DeactivateAgentInput) -> AgentOutput:
        agent_id = AgentId.from_string(input.agent_id)
        agent = await self._repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")

        agent.deactivate()
        await self._repo.save(agent)
        return agent_to_output(agent)
