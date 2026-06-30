"""Adaptador OpenAI-compatible para LLMPort.

Soporta:
- OpenAI (api.openai.com)
- OpenCode (orinoco API — OpenAI-compatible)
- Ollama (localhost:11434 — OpenAI-compatible)
- Cualquier API que hable el protocolo /v1/chat/completions
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from app.application.ports.llm_port import LLMPort, LLMError
from app.infrastructure.config.settings import Settings


class OpenAIAdapter(LLMPort):
    """Adaptador para OpenAI y cualquier API OpenAI-compatible."""

    def __init__(self, settings: Settings) -> None:
        client_kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            client_kwargs["base_url"] = settings.llm_base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = settings.llm_model

    async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                **kwargs,
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception as e:
            raise LLMError(
                message=str(e),
                provider="openai_compatible",
                status_code=getattr(e, "status_code", 0),
            ) from e

    async def generate_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                **kwargs,
            )
            return response.choices[0].message.model_dump()
        except Exception as e:
            raise LLMError(
                message=str(e),
                provider="openai_compatible",
            ) from e
