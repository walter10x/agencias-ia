"""LangGraph StateGraph para el flujo del agente IA.

Flujo:
    START → load_context → call_llm
                              ├── si tool_calls → process_tools → call_llm
                              └── si no → END
"""

from __future__ import annotations

from functools import partial
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.application.ports.llm_port import LLMPort
from app.infrastructure.ai.tools import execute_tool
from app.infrastructure.ai.response_guard import (
    enforce_tool_truth,
    tool_result_succeeded,
)


def normalize_tool_call(tc: dict[str, Any]) -> tuple[str, Any, str]:
    """Normaliza tool_calls OpenAI (`function.name`) y formato plano (`name`).

    Returns:
        (tool_name, arguments, tool_call_id)
    """
    if not isinstance(tc, dict):
        return "", {}, ""
    tool_call_id = str(tc.get("id") or "")
    fn = tc.get("function")
    if isinstance(fn, dict):
        return str(fn.get("name") or ""), fn.get("arguments") or {}, tool_call_id
    return str(tc.get("name") or ""), tc.get("arguments") or {}, tool_call_id


class AgentState(TypedDict):
    """Estado del agente en LangGraph."""

    messages: list[dict[str, Any]]
    system_prompt: str
    agent_config: dict[str, Any]
    client_context: dict[str, Any]
    tools: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    successful_tools: list[str]
    booking_tool_content: str
    final_response: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def load_context_node(state: AgentState) -> AgentState:
    """Nodo 1: Carga contexto adicional (RAG futuro).

    Actualmente es un stub. En el futuro:
    - Buscará en knowledge base del agente
    - Recuperará información relevante del cliente
    - Añadirá contexto al system prompt
    """
    return state


async def call_llm_node(state: AgentState, llm: LLMPort) -> AgentState:
    """Nodo 2: Llama al LLM vía el puerto LLMPort.

    Construye los mensajes completos (system + history + user)
    y los envía al LLM. Si el LLM devuelve tool_calls, se añaden
    al estado para que el edge condicional dirija a process_tools.
    """
    full_messages: list[dict[str, Any]] = [
        {"role": "system", "content": state["system_prompt"]},
        *state["messages"],
    ]

    # Añadir resultados de tools previas si existen
    for tr in state.get("tool_results", []):
        full_messages.append({
            "role": "tool",
            "tool_call_id": tr.get("tool_call_id", ""),
            "content": tr.get("content", ""),
        })

    # Limpiar tool_results después de usarlos para evitar bucle extra
    state["tool_results"] = []

    if state.get("tools"):
        response = await llm.generate_with_tools(
            full_messages,
            tools=state["tools"],
            temperature=0.2,
            max_tokens=1024,
        )
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.get("content") or "",
        }
        if response.get("tool_calls"):
            assistant_msg["tool_calls"] = response["tool_calls"]

        state["messages"].append(assistant_msg)
    else:
        content = await llm.generate(
            full_messages,
            temperature=0.4,
            max_tokens=1024,
        )
        state["messages"].append({"role": "assistant", "content": content})

    return state


async def process_tools_node(state: AgentState) -> AgentState:
    """Nodo 3: Ejecuta las tools solicitadas por el LLM.

    Lee los tool_calls del último mensaje del asistente,
    ejecuta cada tool, y guarda los resultados en tool_results.
    """
    import logging

    logger = logging.getLogger(__name__)

    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else {}
    tool_calls = last_msg.get("tool_calls", []) if isinstance(last_msg, dict) else []

    results: list[dict[str, Any]] = []
    succeeded = list(state.get("successful_tools") or [])
    booking_content = state.get("booking_tool_content") or ""

    for tc in tool_calls:
        tool_name, tool_input, tool_call_id = normalize_tool_call(
            tc if isinstance(tc, dict) else {}
        )

        result_content = await execute_tool(
            tool_name,
            tool_input,
            state.get("client_context", {}),
        )
        logger.info(
            "tool_exec name=%s ok=%s preview=%s",
            tool_name,
            tool_result_succeeded(tool_name, result_content),
            (result_content or "")[:160],
        )

        results.append({
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "content": result_content,
        })
        if tool_name and tool_result_succeeded(tool_name, result_content):
            if tool_name not in succeeded:
                succeeded.append(tool_name)
            if tool_name == "agendar_cita":
                booking_content = result_content

    state["tool_results"] = results
    state["successful_tools"] = succeeded
    state["booking_tool_content"] = booking_content
    return state


# ---------------------------------------------------------------------------
# Conditional Edge
# ---------------------------------------------------------------------------


def should_continue(state: AgentState) -> str:
    """Determina si el flujo debe continuar o terminar.

    - Si el último mensaje del asistente tiene tool_calls → process_tools
    - Si hay tool_results pendientes → call_llm (para que el LLM procese)
    - Si no → END
    """
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else {}

    # Si hay tool_calls en el último mensaje, ejecutar tools
    if isinstance(last_msg, dict) and last_msg.get("tool_calls"):
        return "process_tools"

    # Si hay tool_results sin procesar, volver a llamar al LLM
    if state.get("tool_results"):
        state["tool_results"] = []
        return "call_llm"

    return END


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------


def create_agent_graph(llm: LLMPort) -> StateGraph:
    """Crea el StateGraph del agente IA.

    Args:
        llm: Puerto LLM inyectado (no el adapter concreto).

    Returns:
        StateGraph compilado, listo para ejecutar.
    """
    workflow = StateGraph(AgentState)

    # Registrar nodos
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("call_llm", partial(call_llm_node, llm=llm))
    workflow.add_node("process_tools", process_tools_node)

    # Edges
    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "call_llm")
    workflow.add_conditional_edges(
        "call_llm",
        should_continue,
        {
            "process_tools": "process_tools",
            "call_llm": "call_llm",
            END: END,
        },
    )
    workflow.add_edge("process_tools", "call_llm")

    return workflow.compile()


# ---------------------------------------------------------------------------
# Convenience Runner
# ---------------------------------------------------------------------------


async def run_agent(
    llm: LLMPort,
    system_prompt: str,
    user_message: str,
    agent_config: dict[str, Any],
    client_context: dict[str, Any],
    tools: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Ejecuta el agente IA y devuelve la respuesta final.

    Args:
        llm: Puerto LLM inyectado.
        system_prompt: System prompt construido.
        user_message: Mensaje del usuario sanitizado.
        agent_config: Configuración del agente (nombre, id, etc.).
        client_context: Contexto del cliente (nombre, tipo de negocio, etc.).
        tools: Herramientas en formato OpenAI function calling.
        history: Historial previo de conversación (opcional).

    Returns:
        Respuesta final del agente (texto).
    """
    graph = create_agent_graph(llm)

    initial_state: AgentState = {
        "messages": history or [],
        "system_prompt": system_prompt,
        "agent_config": agent_config,
        "client_context": client_context,
        "tools": tools,
        "tool_results": [],
        "successful_tools": [],
        "booking_tool_content": "",
        "final_response": "",
    }

    # Añadir el mensaje del usuario
    initial_state["messages"].append({"role": "user", "content": user_message})

    final_state = await graph.ainvoke(initial_state)

    # Extraer la respuesta final del último mensaje del asistente
    messages = final_state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content"):
            raw = str(msg["content"])
            return enforce_tool_truth(
                raw,
                final_state.get("successful_tools") or [],
                booking_tool_content=final_state.get("booking_tool_content") or "",
            )

    # Si solo hubo tool_calls sin texto, igual confirmar si la tool guardó
    booked = "agendar_cita" in (final_state.get("successful_tools") or [])
    if booked:
        return enforce_tool_truth(
            "",
            final_state.get("successful_tools") or [],
            booking_tool_content=final_state.get("booking_tool_content") or "",
        )

    return "Lo siento, no pude procesar tu mensaje en este momento."
