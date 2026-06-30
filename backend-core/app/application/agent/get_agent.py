"""Caso de uso: obtener un agente por su ID."""

from __future__ import annotations

from app.application.dtos import AgentOutput, GetAgentInput, agent_to_output
from app.domain.agent.repository import AgentRepository
from app.domain.shared.errors import AgentNotFoundError
from app.domain.shared.value_objects import AgentId


class GetAgentUseCase:
    """Orquesta la búsqueda de un agente por ID."""

    def __init__(self, agent_repo: AgentRepository) -> None:
        self._repo = agent_repo

    async def execute(self, input: GetAgentInput) -> AgentOutput:
        agent_id = AgentId.from_string(input.agent_id)
        agent = await self._repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")
        return agent_to_output(agent)
