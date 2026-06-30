"""Unit tests for AgentGraph — LangGraph StateGraph agent (RED phase — TDD).

Tests the agent graph: nodes (load_context, call_llm, process_tools),
conditional edges, and the full flow runner.
All LLM calls are mocked — this is a pure unit test of graph logic.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.ports.llm_port import LLMPort

# --- Infrastructure layer (does NOT exist yet — RED phase) ---
from app.infrastructure.ai.agent_graph import (
    AgentState,
    create_agent_graph,
    run_agent,
    load_context_node,
    call_llm_node,
    process_tools_node,
    should_continue,
)


# ============================================================================
# Helpers
# ============================================================================

class _MockLLMPort(LLMPort):
    """Mock LLMPort that returns predefined responses for testing the graph.

    Not a MagicMock — a real subclass so isinstance checks pass.
    """

    def __init__(self, text_response: str = "Mock response") -> None:
        self.text_response = text_response
        self.tool_response: dict[str, Any] = {"content": "Mock tool response"}
        self.generate_calls: list[dict[str, Any]] = []
        self.generate_with_tools_calls: list[dict[str, Any]] = []

    async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        self.generate_calls.append({"messages": messages, "kwargs": kwargs})
        return self.text_response

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.generate_with_tools_calls.append({
            "messages": messages, "tools": tools, "kwargs": kwargs,
        })
        return self.tool_response


def _make_state(**overrides: Any) -> AgentState:
    """Build a minimal AgentState for testing individual nodes."""
    return AgentState(
        messages=overrides.get("messages", []),
        system_prompt=str(overrides.get("system_prompt", "You are helpful.")),
        agent_config=overrides.get("agent_config", {"id": "agent-1", "name": "TestBot"}),
        client_context=overrides.get("client_context", {"id": "client-1"}),
        tools=overrides.get("tools", []),
        tool_results=overrides.get("tool_results", []),
        final_response=str(overrides.get("final_response", "")),
    )


# ============================================================================
# AgentState — TypedDict structure
# ============================================================================

class TestAgentState:
    """AgentState TypedDict defines the shape of graph state."""

    def test_has_required_fields(self) -> None:
        """AgentState must include messages, system_prompt, agent_config, etc."""
        state = _make_state()
        assert "messages" in state
        assert "system_prompt" in state
        assert "agent_config" in state
        assert "client_context" in state
        assert "tools" in state
        assert "tool_results" in state
        assert "final_response" in state

    def test_messages_defaults_to_empty_list(self) -> None:
        """Given no messages, when AgentState created, then messages is []."""
        state = _make_state()
        assert state["messages"] == []

    def test_tool_results_defaults_to_empty_list(self) -> None:
        """Given no tool_results, when AgentState created, then tool_results is []."""
        state = _make_state()
        assert state["tool_results"] == []

    def test_tools_defaults_to_empty_list(self) -> None:
        """Given no tools, when AgentState created, then tools is []."""
        state = _make_state()
        assert state["tools"] == []

    def test_final_response_defaults_to_empty_string(self) -> None:
        """Given no final_response, when AgentState created, then final_response is ''."""
        state = _make_state()
        assert state["final_response"] == ""


# ============================================================================
# create_agent_graph() — Graph Construction
# ============================================================================

class TestCreateAgentGraph:
    """RF-AI-07: create_agent_graph() builds a StateGraph with nodes and edges."""

    def test_creates_state_graph(self) -> None:
        """Given an LLMPort, when create_agent_graph() called, then returns compiled graph."""
        llm = _MockLLMPort()
        graph = create_agent_graph(llm)
        assert graph is not None, "Must return a compiled graph object"

    def test_graph_can_be_compiled(self) -> None:
        """Given LLMPort, when create_agent_graph() called, then graph has compile/compiled state."""
        llm = _MockLLMPort()
        graph = create_agent_graph(llm)
        # A compiled graph should have ainvoke method
        assert hasattr(graph, "ainvoke"), "Compiled graph must have ainvoke"


# ============================================================================
# load_context_node — Node 1
# ============================================================================

class TestLoadContextNode:
    """load_context_node is a stub that returns state unchanged (future RAG)."""

    @pytest.mark.asyncio
    async def test_returns_state_unchanged(self) -> None:
        """Given any state, when load_context_node called, then returns same state."""
        state = _make_state(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Test prompt",
        )
        result = await load_context_node(state)
        assert result is state, "load_context_node should return same state object (stub)"
        assert result["messages"] == state["messages"]
        assert result["system_prompt"] == state["system_prompt"]

    @pytest.mark.asyncio
    async def test_preserves_all_fields(self) -> None:
        """Given state with all fields populated, when load_context_node called,
        then all fields are preserved."""
        state = _make_state(
            messages=[{"role": "user", "content": "Hello"}],
            agent_config={"id": "a1", "name": "Bot"},
            client_context={"id": "c1"},
            tools=[{"type": "function", "function": {"name": "t1"}}],
            tool_results=[{"tool_call_id": "1", "content": "done"}],
        )
        result = await load_context_node(state)
        assert result["agent_config"] == {"id": "a1", "name": "Bot"}
        assert result["client_context"] == {"id": "c1"}
        assert len(result["tools"]) == 1


# ============================================================================
# call_llm_node — Node 2
# ============================================================================

class TestCallLLMNode:
    """RF-AI-08: call_llm_node calls LLMPort with messages + system prompt."""

    @pytest.mark.asyncio
    async def test_calls_llm_generate_when_no_tools(self) -> None:
        """Given state without tools, when call_llm_node called,
        then calls llm.generate() and appends assistant message."""
        llm = _MockLLMPort(text_response="Hello! How can I help?")
        state = _make_state(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Be helpful.",
        )

        result = await call_llm_node(state, llm)

        assert len(llm.generate_calls) == 1
        assert len(result["messages"]) == 2  # original user + assistant response
        assert result["messages"][-1]["role"] == "assistant"
        assert result["messages"][-1]["content"] == "Hello! How can I help?"

    @pytest.mark.asyncio
    async def test_calls_llm_generate_with_tools_when_tools_present(self) -> None:
        """Given state with tools, when call_llm_node called,
        then calls llm.generate_with_tools()."""
        llm = _MockLLMPort(text_response="Reponse")
        llm.tool_response = {"content": "Using tool", "tool_calls": []}
        state = _make_state(
            messages=[{"role": "user", "content": "Book appointment"}],
            tools=[{"type": "function", "function": {"name": "agendar_cita"}}],
        )

        await call_llm_node(state, llm)

        assert len(llm.generate_with_tools_calls) == 1
        assert len(llm.generate_calls) == 0  # generate() NOT called

    @pytest.mark.asyncio
    async def test_includes_system_prompt_in_messages(self) -> None:
        """Given system_prompt in state, when call_llm_node called,
        then system prompt is the first message sent to LLM."""
        llm = _MockLLMPort()
        state = _make_state(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="SYSTEM: You are a bar assistant.",
        )

        await call_llm_node(state, llm)

        sent_messages = llm.generate_calls[0]["messages"]
        assert sent_messages[0]["role"] == "system"
        assert sent_messages[0]["content"] == "SYSTEM: You are a bar assistant."

    @pytest.mark.asyncio
    async def test_includes_user_message_in_sent_messages(self) -> None:
        """Given user messages in state, when call_llm_node called,
        then user messages are sent to LLM after system prompt."""
        llm = _MockLLMPort()
        state = _make_state(
            messages=[{"role": "user", "content": "Qué horario tienes?"}],
        )

        await call_llm_node(state, llm)

        sent_messages = llm.generate_calls[0]["messages"]
        user_msgs = [m for m in sent_messages if m["role"] == "user"]
        assert len(user_msgs) >= 1
        assert "Qué horario tienes?" in user_msgs[-1]["content"]

    @pytest.mark.asyncio
    async def test_includes_tool_results_in_messages(self) -> None:
        """Given tool_results in state, when call_llm_node called,
        then tool results are included as tool-role messages."""
        llm = _MockLLMPort()
        state = _make_state(
            messages=[{"role": "user", "content": "Book"}],
            tool_results=[
                {"tool_call_id": "call_1", "content": "Cita agendada para mañana 10am"},
            ],
        )

        await call_llm_node(state, llm)

        sent_messages = llm.generate_calls[0]["messages"]
        tool_msgs = [m for m in sent_messages if m.get("role") == "tool"]
        assert len(tool_msgs) >= 1
        assert "Cita agendada" in tool_msgs[0]["content"]

    @pytest.mark.asyncio
    async def test_passes_temperature_and_max_tokens(self) -> None:
        """Given state, when call_llm_node called, then passes temperature and max_tokens."""
        llm = _MockLLMPort()
        state = _make_state(
            messages=[{"role": "user", "content": "Hi"}],
        )

        await call_llm_node(state, llm)

        kwargs = llm.generate_calls[0]["kwargs"]
        assert kwargs.get("temperature") == 0.7
        assert kwargs.get("max_tokens") == 1024

    @pytest.mark.asyncio
    async def test_appends_assistant_message_with_tool_calls(self) -> None:
        """Given LLM returns tool_calls, when call_llm_node called,
        then assistant message includes tool_calls."""
        llm = _MockLLMPort()
        llm.tool_response = {
            "content": "",
            "tool_calls": [
                {"id": "call_1", "function": {"name": "agendar_cita", "arguments": '{"input":"mañana"}'}},
            ],
        }
        state = _make_state(
            messages=[{"role": "user", "content": "Agenda cita mañana"}],
            tools=[{"type": "function", "function": {"name": "agendar_cita"}}],
        )

        result = await call_llm_node(state, llm)

        last_msg = result["messages"][-1]
        assert last_msg["role"] == "assistant"
        assert "tool_calls" in last_msg
        assert len(last_msg["tool_calls"]) == 1

    @pytest.mark.asyncio
    async def test_returns_state_with_updated_messages(self) -> None:
        """Given any state, when call_llm_node called, then returns state (not None)."""
        llm = _MockLLMPort()
        state = _make_state()

        result = await call_llm_node(state, llm)

        assert result is state
        assert len(result["messages"]) > 0


# ============================================================================
# process_tools_node — Node 3
# ============================================================================

class TestProcessToolsNode:
    """RF-AI-09: process_tools_node executes tools via n8n webhook."""

    @pytest.mark.asyncio
    async def test_executes_tool_from_tool_calls(self) -> None:
        """Given state with assistant msg containing tool_calls,
        when process_tools_node called, then executes tools and adds results."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "Agenda cita"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "name": "agendar_cita",
                            "arguments": {"input": "mañana 10am"},
                        },
                    ],
                },
            ],
        )

        with patch(
            "app.infrastructure.ai.agent_graph.execute_tool",
            new_callable=AsyncMock,
            return_value="Cita agendada exitosamente",
        ) as mock_execute:
            result = await process_tools_node(state)

        mock_execute.assert_awaited_once_with("agendar_cita", "mañana 10am")
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["tool_call_id"] == "call_abc"
        assert result["tool_results"][0]["tool_name"] == "agendar_cita"
        assert "Cita agendada" in result["tool_results"][0]["content"]

    @pytest.mark.asyncio
    async def test_executes_multiple_tool_calls(self) -> None:
        """Given assistant msg with multiple tool_calls, when process_tools_node called,
        then executes ALL tools."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "Consulta precios y agenda"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "c1", "name": "consultar_precios", "arguments": {"input": "corte"}},
                        {"id": "c2", "name": "agendar_cita", "arguments": {"input": "viernes 3pm"}},
                    ],
                },
            ],
        )

        with patch(
            "app.infrastructure.ai.agent_graph.execute_tool",
            new_callable=AsyncMock,
            side_effect=["Precio: $50", "Cita agendada"],
        ) as mock_execute:
            result = await process_tools_node(state)

        assert mock_execute.await_count == 2
        assert len(result["tool_results"]) == 2

    @pytest.mark.asyncio
    async def test_handles_tool_execution_error(self) -> None:
        """Given n8n webhook returns error, when process_tools_node called,
        then error is captured in tool_result content."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "Agenda cita"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "call_err", "name": "agendar_cita", "arguments": {"input": "test"}},
                    ],
                },
            ],
        )

        with patch(
            "app.infrastructure.ai.agent_graph.execute_tool",
            new_callable=AsyncMock,
            return_value="Error ejecutando tool 'agendar_cita': Connection refused",
        ) as mock_execute:
            result = await process_tools_node(state)

        assert len(result["tool_results"]) == 1
        assert "Error" in result["tool_results"][0]["content"]
        assert result["tool_results"][0]["tool_call_id"] == "call_err"

    @pytest.mark.asyncio
    async def test_no_tool_calls_empty_results(self) -> None:
        """Given assistant msg without tool_calls, when process_tools_node called,
        then tool_results remains empty."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ],
        )

        result = await process_tools_node(state)

        assert result["tool_results"] == []

    @pytest.mark.asyncio
    async def test_extracts_input_from_string_arguments(self) -> None:
        """Given tool call with string arguments (not dict), when process_tools_node called,
        then handles string input."""
        state = _make_state(
            messages=[
                {"role": "assistant", "content": "",
                 "tool_calls": [
                     {"id": "c1", "name": "test_tool", "arguments": "direct string input"},
                 ]},
            ],
        )

        with patch(
            "app.infrastructure.ai.agent_graph.execute_tool",
            new_callable=AsyncMock,
            return_value="OK",
        ) as mock_execute:
            await process_tools_node(state)

        mock_execute.assert_awaited_once_with("test_tool", "direct string input")


# ============================================================================
# should_continue — Conditional Edge
# ============================================================================

class TestShouldContinue:
    """RF-AI-10, RF-AI-11: Conditional routing based on tool_calls presence."""

    def test_routes_to_process_tools_when_tool_calls_present(self) -> None:
        """Given last assistant message has tool_calls, when should_continue called,
        then returns 'process_tools'."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "Book"},
                {"role": "assistant", "content": "", "tool_calls": [{"name": "test"}]},
            ],
        )
        result = should_continue(state)
        assert result == "process_tools"

    def test_routes_to_end_when_no_tool_calls(self) -> None:
        """Given last assistant message has NO tool_calls, when should_continue called,
        then returns END."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ],
        )
        result = should_continue(state)
        # END is a string sentinel from langgraph
        assert result != "process_tools"
        assert result != "call_llm"

    def test_routes_to_call_llm_when_tool_results_present(self) -> None:
        """Given tool_results exist but last message has no tool_calls,
        when should_continue called, then returns 'call_llm'."""
        state = _make_state(
            messages=[
                {"role": "user", "content": "Book"},
                {"role": "assistant", "content": "Processing..."},
            ],
            tool_results=[{"tool_call_id": "1", "content": "Done"}],
        )
        result = should_continue(state)
        assert result == "call_llm"

    def test_clears_tool_results_after_routing_to_call_llm(self) -> None:
        """Given tool_results present, when should_continue routes to call_llm,
        then tool_results are cleared."""
        state = _make_state(
            messages=[
                {"role": "assistant", "content": "OK"},
            ],
            tool_results=[{"tool_call_id": "1", "content": "Done"}],
        )
        should_continue(state)
        assert state["tool_results"] == []

    def test_empty_messages_routes_to_end(self) -> None:
        """Given state with empty messages, when should_continue called,
        then returns END."""
        state = _make_state(messages=[])
        result = should_continue(state)
        # No messages → no tool_calls → END
        assert result != "process_tools"


# ============================================================================
# create_agent_graph() — End-to-End Flow (mocked LLM)
# ============================================================================

class TestAgentGraphFullFlow:
    """RF-AI-10, RF-AI-11: Full graph execution with mocked LLM."""

    @pytest.mark.asyncio
    async def test_simple_message_without_tools(self) -> None:
        """Given user message + no tools, when graph invoked,
        then LLM generates direct response → END."""
        llm = _MockLLMPort(text_response="¡Hola! ¿En qué puedo ayudarte?")
        graph = create_agent_graph(llm)

        state = _make_state(
            messages=[{"role": "user", "content": "Hola"}],
            system_prompt="Eres un asistente amable.",
        )

        final_state = await graph.ainvoke(state)

        assert len(final_state["messages"]) >= 2
        last_msg = final_state["messages"][-1]
        assert last_msg["role"] == "assistant"
        assert "Hola" in last_msg["content"] or "puedo ayudarte" in last_msg["content"]

    @pytest.mark.asyncio
    async def test_message_with_tool_calls(self) -> None:
        """Given user message + tools, when LLM returns tool_calls,
        then graph routes: call_llm → process_tools → call_llm → END."""
        llm = _MockLLMPort()

        # First call: LLM returns tool_calls
        # Second call: LLM returns final response
        call_count = 0

        async def dynamic_generate_with_tools(
            messages: list[dict[str, Any]], tools: list[dict[str, Any]], **kwargs: Any
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "agendar_cita",
                                "arguments": '{"input":"mañana 10am"}',
                            },
                        }
                    ],
                }
            return {"content": "¡Listo! Tu cita fue agendada para mañana a las 10am.", "tool_calls": []}

        async def dynamic_generate(messages: list[dict[str, Any]], **kwargs: Any) -> str:
            return "Final response"

        llm.generate_with_tools = dynamic_generate_with_tools  # type: ignore[method-assign]
        llm.generate = dynamic_generate  # type: ignore[method-assign]

        graph = create_agent_graph(llm)

        state = _make_state(
            messages=[{"role": "user", "content": "Agenda cita mañana 10am"}],
            system_prompt="Eres un asistente de peluquería.",
            tools=[{"type": "function", "function": {"name": "agendar_cita"}}],
        )

        with patch(
            "app.infrastructure.ai.agent_graph.execute_tool",
            new_callable=AsyncMock,
            return_value="Cita agendada OK",
        ):
            final_state = await graph.ainvoke(state)

        assert call_count == 2, "LLM should be called twice (tool call + final response)"
        last_msg = final_state["messages"][-1]
        assert "agendada" in last_msg["content"].lower()

    @pytest.mark.asyncio
    async def test_flow_enters_load_context_first(self) -> None:
        """Given graph invocation, when executed, then load_context is the entry point."""
        llm = _MockLLMPort(text_response="Response")
        graph = create_agent_graph(llm)

        state = _make_state(
            messages=[{"role": "user", "content": "Test"}],
            system_prompt="System",
        )

        # load_context is a stub; graph should still work
        final_state = await graph.ainvoke(state)
        assert len(final_state["messages"]) >= 2


# ============================================================================
# run_agent() — Convenience Runner
# ============================================================================

class TestRunAgent:
    """run_agent() provides a simplified interface for full agent execution."""

    @pytest.mark.asyncio
    async def test_returns_final_response_string(self) -> None:
        """Given all params, when run_agent() called, then returns str response."""
        llm = _MockLLMPort(text_response="Respuesta final del agente.")

        result = await run_agent(
            llm=llm,
            system_prompt="Eres útil.",
            user_message="Hola",
            agent_config={"id": "a1", "name": "Bot"},
            client_context={"id": "c1"},
            tools=[],
        )

        assert isinstance(result, str)
        assert result == "Respuesta final del agente."

    @pytest.mark.asyncio
    async def test_includes_user_message_in_initial_state(self) -> None:
        """Given user_message, when run_agent() called,
        then user message is added to messages."""
        llm = _MockLLMPort(text_response="OK")

        await run_agent(
            llm=llm,
            system_prompt="Prompt",
            user_message="Mensaje de prueba",
            agent_config={},
            client_context={},
            tools=[],
        )

        # Check that the user message was sent
        sent = llm.generate_calls[0]["messages"]
        user_msgs = [m for m in sent if m["role"] == "user"]
        assert any("Mensaje de prueba" in m["content"] for m in user_msgs)

    @pytest.mark.asyncio
    async def test_includes_history_when_provided(self) -> None:
        """Given history list, when run_agent() called,
        then history messages are prepended."""
        llm = _MockLLMPort(text_response="OK")
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        await run_agent(
            llm=llm,
            system_prompt="Prompt",
            user_message="New question",
            agent_config={},
            client_context={},
            tools=[],
            history=history,
        )

        sent = llm.generate_calls[0]["messages"]
        assert sent[1]["content"] == "Previous question"
        assert sent[2]["content"] == "Previous answer"

    @pytest.mark.asyncio
    async def test_extracts_last_assistant_message(self) -> None:
        """Given multiple assistant messages, when run_agent() called,
        then returns the LAST assistant message content."""
        # The mock returns a simple text, the runner extracts it
        llm = _MockLLMPort(text_response="Último mensaje del asistente.")

        result = await run_agent(
            llm=llm,
            system_prompt="Prompt",
            user_message="Test",
            agent_config={},
            client_context={},
            tools=[],
        )

        assert result == "Último mensaje del asistente."

    @pytest.mark.asyncio
    async def test_returns_fallback_when_no_assistant_message(self) -> None:
        """Given state with no assistant messages, when run_agent() called,
        then returns fallback message."""
        llm = _MockLLMPort(text_response="")  # empty response

        result = await run_agent(
            llm=llm,
            system_prompt="Prompt",
            user_message="Test",
            agent_config={},
            client_context={},
            tools=[],
        )

        # Should return fallback, not empty string
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_passes_agent_config_to_state(self) -> None:
        """Given agent_config, when run_agent() called, then config is in initial state."""
        llm = _MockLLMPort(text_response="OK")
        agent_config = {"id": "agent-42", "name": "SuperBot"}

        await run_agent(
            llm=llm,
            system_prompt="Prompt",
            user_message="Hi",
            agent_config=agent_config,
            client_context={"id": "c1"},
            tools=[],
        )

        # Config should be in the system prompt area... but more importantly, it's passed correctly.
        # The test verifies the call happened without error.
        assert len(llm.generate_calls) > 0

    @pytest.mark.asyncio
    async def test_passes_tools_to_graph(self) -> None:
        """Given tools list, when run_agent() called with no tools,
        then generate() is used (not generate_with_tools)."""
        llm = _MockLLMPort(text_response="OK")

        await run_agent(
            llm=llm,
            system_prompt="Prompt",
            user_message="Hi",
            agent_config={},
            client_context={},
            tools=[],
        )

        assert len(llm.generate_calls) == 1
        assert len(llm.generate_with_tools_calls) == 0


# ============================================================================
# Graph Node Edge Cases
# ============================================================================

class TestAgentGraphEdgeCases:
    """Edge cases for the agent graph."""

    @pytest.mark.asyncio
    async def test_handles_conversation_with_many_messages(self) -> None:
        """Given state with many conversation turns, when graph runs,
        then all messages are included."""
        llm = _MockLLMPort(text_response="Response #10")
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(10)
        ]

        state = _make_state(messages=messages)
        result = await call_llm_node(state, llm)

        # All original messages should still be present
        assert len(result["messages"]) >= 11  # original 10 + 1 new assistant

    @pytest.mark.asyncio
    async def test_generate_with_tools_when_tools_empty(self) -> None:
        """Given empty tools list, when call_llm_node called,
        then uses generate() not generate_with_tools()."""
        llm = _MockLLMPort()
        state = _make_state(tools=[])

        await call_llm_node(state, llm)

        assert len(llm.generate_calls) == 1
        assert len(llm.generate_with_tools_calls) == 0

    @pytest.mark.asyncio
    async def test_process_tools_handles_missing_tool_call_id(self) -> None:
        """Given tool_call without id, when process_tools_node called,
        then defaults to empty string."""
        state = _make_state(
            messages=[
                {"role": "assistant", "content": "",
                 "tool_calls": [{"name": "test", "arguments": {"input": "ok"}}]},
            ],
        )

        with patch(
            "app.infrastructure.ai.agent_graph.execute_tool",
            new_callable=AsyncMock,
            return_value="OK",
        ):
            result = await process_tools_node(state)

        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["tool_call_id"] == ""
