"""Caso de uso: eliminar físicamente un agente."""

from __future__ import annotations

from app.application.dtos import DeleteAgentInput
from app.domain.agent.repository import AgentRepository
from app.domain.shared.errors import AgentNotFoundError, ForbiddenError
from app.domain.shared.value_objects import AgentId, ClientId


class DeleteAgentUseCase:
    """Orquesta la eliminación física de un agente."""

    def __init__(self, agent_repo: AgentRepository) -> None:
        self._repo = agent_repo

    async def execute(self, input: DeleteAgentInput, client_id: str | None = None) -> None:
        agent_id = AgentId.from_string(input.agent_id)
        if client_id is not None:
            agent = await self._repo.find_by_id(agent_id)
            if agent is None:
                raise AgentNotFoundError(f"Agent not found: {agent_id}")
            if agent.client_id != ClientId.from_string(client_id):
                raise ForbiddenError("Agent does not belong to this client")
        await self._repo.delete(agent_id)
        return None
