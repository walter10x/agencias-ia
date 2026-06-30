"""Tests unitarios para la entidad Agent."""

import pytest

from app.domain.agent.entity import Agent, AgentTool
from app.domain.shared.value_objects import ClientId


class TestAgentCreation:
    def test_creates_with_minimum_data(self) -> None:
        agent = Agent(
            client_id=ClientId.generate(),
            name="Bot Peluquería",
            personality="Eres un asistente amable de una peluquería. "
                         "Ayudas a agendar citas y responder preguntas.",
        )
        assert agent.name == "Bot Peluquería"
        assert len(agent.personality) >= 10
        assert agent.is_active is True
        assert len(agent.tools) == 0

    def test_raises_on_empty_name(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Agent(
                client_id=ClientId.generate(),
                name="",
                personality="Eres un asistente muy amable de un negocio local.",
            )

    def test_raises_on_short_personality(self) -> None:
        with pytest.raises(ValueError, match="10 chars"):
            Agent(
                client_id=ClientId.generate(),
                name="Bot",
                personality="Muy corto",
            )


class TestAgentBehavior:
    def test_add_tool(self) -> None:
        agent = self._create_agent()
        tool = AgentTool(name="agendar_cita", description="Agenda una cita")
        agent.add_tool(tool)
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "agendar_cita"

    def test_add_duplicate_tool_ignored(self) -> None:
        agent = self._create_agent()
        tool = AgentTool(name="agendar_cita", description="Agenda una cita")
        agent.add_tool(tool)
        agent.add_tool(tool)
        assert len(agent.tools) == 1

    def test_remove_tool(self) -> None:
        agent = self._create_agent()
        agent.add_tool(AgentTool(name="test", description="test"))
        agent.remove_tool("test")
        assert len(agent.tools) == 0

    def test_deactivate_agent(self) -> None:
        agent = self._create_agent()
        agent.deactivate()
        assert agent.is_active is False

    def test_update_personality(self) -> None:
        agent = self._create_agent()
        new_prompt = "Eres un asistente serio y profesional. Respondes concisamente."
        agent.update_personality(new_prompt)
        assert agent.personality == new_prompt

    def test_update_personality_raises_on_short(self) -> None:
        agent = self._create_agent()
        with pytest.raises(ValueError, match="10 chars"):
            agent.update_personality("corto")

    @staticmethod
    def _create_agent() -> Agent:
        return Agent(
            client_id=ClientId.generate(),
            name="Test Agent",
            personality="Eres un asistente muy amable de prueba.",
        )
