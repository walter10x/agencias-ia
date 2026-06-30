"""Puerto de repositorio para Agent (DRIVEN PORT)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.agent.entity import Agent
from app.domain.shared.value_objects import AgentId, ClientId


class AgentRepository(ABC):
    """Interfaz de repositorio para el agregado Agent."""

    @abstractmethod
    async def save(self, agent: Agent) -> None:
        ...

    @abstractmethod
    async def find_by_id(self, agent_id: AgentId) -> Optional[Agent]:
        ...

    @abstractmethod
    async def find_active_by_client(self, client_id: ClientId) -> list[Agent]:
        """Devuelve todos los agentes activos de un cliente."""
        ...

    @abstractmethod
    async def delete(self, agent_id: AgentId) -> None:
        ...
