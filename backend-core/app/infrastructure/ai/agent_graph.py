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


class AgentState(TypedDict):
    """Estado del agente en LangGraph."""

    messages: list[dict[str, Any]]
    system_prompt: str
    agent_config: dict[str, Any]
    client_context: dict[str, Any]
    tools: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
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
            temperature=0.7,
            max_tokens=1024,
        )
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.get("content", ""),
        }
        if response.get("tool_calls"):
            assistant_msg["tool_calls"] = response["tool_calls"]

        state["messages"].append(assistant_msg)
    else:
        content = await llm.generate(
            full_messages,
            temperature=0.7,
            max_tokens=1024,
        )
        state["messages"].append({"role": "assistant", "content": content})

    return state


async def process_tools_node(state: AgentState) -> AgentState:
    """Nodo 3: Ejecuta las tools solicitadas por el LLM.

    Lee los tool_calls del último mensaje del asistente,
    ejecuta cada tool, y guarda los resultados en tool_results.
    """
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else {}
    tool_calls = last_msg.get("tool_calls", []) if isinstance(last_msg, dict) else []

    results: list[dict[str, Any]] = []
    for tc in tool_calls:
        tool_name = tc.get("name", "")
        tool_input = tc.get("arguments", {})
        tool_call_id = tc.get("id", "")

        # Se pasan los argumentos completos (dict o string) y el contexto
        # del tenant: las tools nativas necesitan el client_id para
        # ejecutar los use cases scoped por negocio.
        result_content = await execute_tool(
            tool_name,
            tool_input,
            state.get("client_context", {}),
        )

        results.append({
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "content": result_content,
        })

    state["tool_results"] = results
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
        "final_response": "",
    }

    # Añadir el mensaje del usuario
    initial_state["messages"].append({"role": "user", "content": user_message})

    final_state = await graph.ainvoke(initial_state)

    # Extraer la respuesta final del último mensaje del asistente
    messages = final_state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content"):
            return str(msg["content"])

    return "Lo siento, no pude procesar tu mensaje en este momento."
