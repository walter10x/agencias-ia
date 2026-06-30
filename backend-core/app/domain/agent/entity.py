"""Entidad Agent: configuración de un agente IA.

Cada agente pertenece a UN cliente y define cómo responde
a los mensajes de WhatsApp de ese negocio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.domain.shared.entity import HasTimestamps
from app.domain.shared.value_objects import AgentId, ClientId


@dataclass
class AgentTool:
    """Herramienta disponible para el agente IA."""

    name: str
    description: str
    endpoint: str = ""


@dataclass
class Agent(HasTimestamps):
    """Configuración de un agente IA para un cliente específico.

    Invariantes:
    - client_id no puede ser nulo
    - name no puede estar vacío
    - personality (system prompt) debe tener al menos 10 caracteres
    - tools debe ser una lista (puede estar vacía)
    """

    id: UUID = field(default_factory=uuid4)
    client_id: ClientId = field(default_factory=ClientId.generate)
    name: str = ""
    personality: str = ""
    tools: list[AgentTool] = field(default_factory=list)
    knowledge_base_refs: list[str] = field(default_factory=list)
    is_active: bool = True

    def __post_init__(self) -> None:
        self._init_timestamps()
        if not self.name.strip():
            raise ValueError("Agent name cannot be empty")
        if len(self.personality.strip()) < 10:
            raise ValueError("Agent personality must be at least 10 chars")

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        self.is_active = True
        self.touch()

    def add_tool(self, tool: AgentTool) -> None:
        if not any(t.name == tool.name for t in self.tools):
            self.tools.append(tool)
            self.touch()

    def remove_tool(self, tool_name: str) -> None:
        self.tools = [t for t in self.tools if t.name != tool_name]
        self.touch()

    def update_personality(self, new_personality: str) -> None:
        if len(new_personality.strip()) < 10:
            raise ValueError("Agent personality must be at least 10 chars")
        self.personality = new_personality.strip()
        self.touch()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Agent):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
