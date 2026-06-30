"""Conversión de AgentTool (dominio) a LangChain Tool (ejecutable).

Los tools definidos en el agente (ej: agendar_cita, consultar_precios)
se convierten en herramientas ejecutables que LangGraph puede invocar.
"""

from __future__ import annotations

from typing import Any

from app.domain.agent.entity import AgentTool
from app.infrastructure.config.settings import get_settings


def agent_tools_to_openai_format(tools: list[AgentTool]) -> list[dict[str, Any]]:
    """Convierte AgentTool a formato OpenAI function calling.

    Args:
        tools: Lista de tools definidas en la configuración del agente.

    Returns:
        Lista de tool definitions en formato OpenAI.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": f"Input para la herramienta {tool.name}",
                        }
                    },
                    "required": ["input"],
                },
            },
        }
        for tool in tools
    ]


async def execute_tool(tool_name: str, tool_input: str) -> str:
    """Ejecuta una herramienta del agente.

    Actualmente, las tools delegan a n8n vía HTTP.
    En el futuro, podrían ejecutarse localmente o vía múltiples backends.

    Args:
        tool_name: Nombre de la herramienta a ejecutar.
        tool_input: Input en formato JSON string.

    Returns:
        Resultado de la ejecución como string.
    """
    settings = get_settings()

    if not settings.n8n_url:
        return f"Tool '{tool_name}' no está configurada (n8n_url vacío)."

    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Content-Type": "application/json"}
            if settings.n8n_api_key:
                headers["X-N8N-API-KEY"] = settings.n8n_api_key

            response = await client.post(
                f"{settings.n8n_url}/webhook/{tool_name}",
                json={"input": tool_input},
                headers=headers,
            )
            response.raise_for_status()
            return response.text
    except Exception as e:
        return f"Error ejecutando tool '{tool_name}': {e}"
