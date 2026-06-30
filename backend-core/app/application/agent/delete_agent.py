"""Caso de uso: eliminar físicamente un agente."""

from __future__ import annotations

from app.application.dtos import DeleteAgentInput
from app.domain.agent.repository import AgentRepository
from app.domain.shared.value_objects import AgentId


class DeleteAgentUseCase:
    """Orquesta la eliminación física de un agente."""

    def __init__(self, agent_repo: AgentRepository) -> None:
        self._repo = agent_repo

    async def execute(self, input: DeleteAgentInput) -> None:
        agent_id = AgentId.from_string(input.agent_id)
        await self._repo.delete(agent_id)
        return None
