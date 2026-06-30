"""Caso de uso: listar agentes activos de un cliente."""

from __future__ import annotations

from app.application.dtos import AgentOutput, ListAgentsByClientInput, agent_to_output
from app.domain.agent.repository import AgentRepository
from app.domain.shared.value_objects import ClientId


class ListAgentsByClientUseCase:
    """Orquesta la consulta de agentes activos por cliente."""

    def __init__(self, agent_repo: AgentRepository) -> None:
        self._repo = agent_repo

    async def execute(self, input: ListAgentsByClientInput) -> list[AgentOutput]:
        client_id = ClientId.from_string(input.client_id)
        agents = await self._repo.find_active_by_client(client_id)
        return [agent_to_output(a) for a in agents]
