"""Puerto LLM — interfaz abstracta para generación de texto vía IA.

La capa de aplicación define ESTE puerto. La infraestructura
provee los adaptadores concretos (OpenAI, Anthropic, etc.).
El dominio NO conoce qué LLM se usa.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMError(Exception):
    """Error genérico del puerto LLM — lanzado por cualquier adaptador."""

    def __init__(self, message: str, provider: str = "", status_code: int = 0) -> None:
        self.message = message
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


class LLMPort(ABC):
    """Interfaz abstracta para invocar un LLM.

    Cualquier adaptador (OpenAI, Anthropic, Ollama, etc.)
    debe implementar este puerto.
    """

    @abstractmethod
    async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Genera una respuesta de texto a partir de una lista de mensajes.

        Args:
            messages: Lista de mensajes con formato:
                [{"role": "system", "content": "..."},
                 {"role": "user", "content": "..."},
                 {"role": "assistant", "content": "..."}]
            **kwargs: Parámetros adicionales (temperature, max_tokens, tools, etc.)

        Returns:
            Texto generado por el LLM.

        Raises:
            LLMError: Si el proveedor falla (timeout, rate limit, etc.)
        """
        ...

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Genera una respuesta que puede incluir tool calls.

        Args:
            messages: Historial de conversación.
            tools: Definición de tools en formato OpenAI function calling.
            **kwargs: Parámetros adicionales.

        Returns:
            Respuesta completa del LLM (puede contener content y/o tool_calls).

        Raises:
            LLMError: Si el proveedor falla.
        """
        ...
