"""Caso de uso: actualizar configuración de un agente."""

from __future__ import annotations

from app.application.dtos import AgentOutput, UpdateAgentInput, agent_to_output
from app.domain.agent.entity import AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.shared.errors import AgentNotFoundError, InvalidAgentError
from app.domain.shared.value_objects import AgentId


class UpdateAgentUseCase:
    """Orquesta la actualización parcial de un agente."""

    def __init__(self, agent_repo: AgentRepository) -> None:
        self._repo = agent_repo

    async def execute(self, input: UpdateAgentInput) -> AgentOutput:
        agent_id = AgentId.from_string(input.agent_id)
        agent = await self._repo.find_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")

        if input.name is not None:
            if not input.name.strip():
                raise InvalidAgentError("Agent name cannot be empty")
            agent.name = input.name.strip()
            agent.touch()

        if input.personality is not None:
            agent.update_personality(input.personality)

        if input.tools is not None:
            agent.tools = [
                AgentTool(name=t.name, description=t.description, endpoint=t.endpoint)
                for t in input.tools
            ]
            agent.touch()

        if input.knowledge_base_refs is not None:
            agent.knowledge_base_refs = list(input.knowledge_base_refs)
            agent.touch()

        await self._repo.save(agent)
        return agent_to_output(agent)
