"""Caso de uso: crear un nuevo agente IA para un cliente."""

from __future__ import annotations

from app.application.dtos import AgentOutput, CreateAgentInput, agent_to_output
from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import InvalidAgentError
from app.domain.shared.value_objects import ClientId


class CreateAgentUseCase:
    """Orquesta la creación de un agente validando que el cliente exista."""

    def __init__(
        self,
        agent_repo: AgentRepository,
        client_repo: ClientRepository,
    ) -> None:
        self._agent_repo = agent_repo
        self._client_repo = client_repo

    async def execute(self, input: CreateAgentInput) -> AgentOutput:
        client_id = ClientId.from_string(input.client_id)

        if not input.name.strip():
            raise InvalidAgentError("Agent name cannot be empty")

        if len(input.personality.strip()) < 10:
            raise ValueError("Agent personality must be at least 10 chars")

        client = await self._client_repo.find_by_id(client_id)
        if client is None:
            raise InvalidAgentError(f"Client not found: {client_id}")

        tools = [
            AgentTool(name=t.name, description=t.description, endpoint=t.endpoint)
            for t in input.tools
        ]

        agent = Agent(
            client_id=client_id,
            name=input.name.strip(),
            personality=input.personality.strip(),
            tools=tools,
            knowledge_base_refs=list(input.knowledge_base_refs),
        )

        await self._agent_repo.save(agent)
        return agent_to_output(agent)
