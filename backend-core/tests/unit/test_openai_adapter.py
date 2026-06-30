"""Unit tests for OpenAIAdapter — Infrastructure LLM adapter (RED phase — TDD).

Tests the OpenAI-compatible adapter with mocked AsyncOpenAI client.
Covers: OpenAI, OpenCode, Ollama (all via same adapter with base_url).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.ports.llm_port import LLMPort, LLMError

# --- Infrastructure layer (does NOT exist yet — RED phase) ---
from app.infrastructure.ai.openai_adapter import OpenAIAdapter
from app.infrastructure.config.settings import Settings, get_settings


# ============================================================================
# Helpers
# ============================================================================

def _make_chat_completion_mock(content: str = "Hello!") -> MagicMock:
    """Build a mock AsyncOpenAI response that matches the expected shape."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_tool_call_response(content: str = "", tool_calls: list[dict[str, Any]] | None = None) -> MagicMock:
    """Build a mock AsyncOpenAI response that includes tool_calls."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls or []
    # model_dump() returns a dict representation for generate_with_tools
    mock_message.model_dump.return_value = {
        "content": content,
        "tool_calls": [
            {
                "id": tc.get("id", ""),
                "function": {
                    "name": tc.get("function", {}).get("name", ""),
                    "arguments": tc.get("function", {}).get("arguments", "{}"),
                },
            }
            for tc in (tool_calls or [])
        ],
    }
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_settings(**overrides: Any) -> Settings:
    """Build a Settings instance with LLM fields for testing."""
    return Settings(
        llm_provider=str(overrides.get("llm_provider", "openai")),
        llm_api_key=str(overrides.get("llm_api_key", "sk-test-key")),
        llm_base_url=str(overrides.get("llm_base_url", "")),
        llm_model=str(overrides.get("llm_model", "gpt-4o-mini")),
    )


# ============================================================================
# OpenAIAdapter — Constructor
# ============================================================================

class TestOpenAIAdapterCreation:
    """RF-AI-02, RF-AI-03: Adapter creation with api_key and optional base_url."""

    def test_is_llm_port_subclass(self) -> None:
        """OpenAIAdapter must implement LLMPort."""
        assert issubclass(OpenAIAdapter, LLMPort)

    def test_creates_with_api_key(self) -> None:
        """Given settings with api_key, when adapter created, then AsyncOpenAI receives api_key."""
        settings = _make_settings(llm_api_key="sk-abc123")
        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI") as mock_client_cls:
            OpenAIAdapter(settings)
            mock_client_cls.assert_called_once()
            call_kwargs = mock_client_cls.call_args.kwargs
            assert call_kwargs.get("api_key") == "sk-abc123"

    def test_creates_with_base_url(self) -> None:
        """Given settings with base_url, when adapter created, then AsyncOpenAI receives base_url."""
        settings = _make_settings(
            llm_api_key="sk-abc",
            llm_base_url="http://localhost:11434/v1",
        )
        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI") as mock_client_cls:
            OpenAIAdapter(settings)
            call_kwargs = mock_client_cls.call_args.kwargs
            assert call_kwargs.get("base_url") == "http://localhost:11434/v1"

    def test_creates_with_empty_api_key(self) -> None:
        """Given settings with empty api_key (Ollama), when adapter created, then still succeeds."""
        settings = _make_settings(llm_api_key="", llm_base_url="http://localhost:11434/v1")
        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI") as mock_client_cls:
            adapter = OpenAIAdapter(settings)
            assert adapter is not None
            call_kwargs = mock_client_cls.call_args.kwargs
            # api_key not passed when empty
            assert "api_key" not in call_kwargs or call_kwargs.get("api_key") == ""

    def test_stores_model_from_settings(self) -> None:
        """Given settings with llm_model, when adapter created, then model stored internally."""
        settings = _make_settings(llm_model="gpt-4o")
        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI"):
            adapter = OpenAIAdapter(settings)
            assert adapter._model == "gpt-4o"

    def test_default_model_is_gpt_4o_mini(self) -> None:
        """Given settings without explicit model, when adapter created, then uses default."""
        settings = _make_settings()
        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI"):
            adapter = OpenAIAdapter(settings)
            assert adapter._model == "gpt-4o-mini"


# ============================================================================
# OpenAIAdapter — generate()
# ============================================================================

class TestOpenAIAdapterGenerate:
    """RF-AI-02: generate() sends messages to ChatOpenAI and returns string."""

    @pytest.mark.asyncio
    async def test_generate_calls_chat_completions(self) -> None:
        """Given messages list, when generate() called, then AsyncOpenAI receives them."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi!"},
        ]
        mock_response = _make_chat_completion_mock("Hello there!")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            result = await adapter.generate(messages)

        assert result == "Hello there!"
        mock_client.chat.completions.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_returns_string(self) -> None:
        """Given valid messages, when generate() called, then returns str type."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Test"}]
        mock_response = _make_chat_completion_mock("Response text")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            result = await adapter.generate(messages)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_handles_empty_content(self) -> None:
        """Given response with empty content, when generate() called, then returns ''."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "?"}]
        mock_response = _make_chat_completion_mock(content="")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            result = await adapter.generate(messages)

        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_handles_none_content(self) -> None:
        """Given response with None content (e.g., tool-only response), when generate() called,
        then returns '' safely."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "do something"}]
        mock_response = _make_chat_completion_mock(content=None)  # type: ignore[arg-type]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            result = await adapter.generate(messages)

        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_passes_model_to_api(self) -> None:
        """Given settings with custom model, when generate() called, then model sent to API."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Hi"}]
        mock_response = _make_chat_completion_mock("Hey")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        settings = _make_settings(llm_model="gpt-4-turbo")
        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(settings)
            await adapter.generate(messages)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_generate_passes_temperature_via_kwargs(self) -> None:
        """Given temperature kwarg, when generate() called, then temperature sent to API."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Creative?"}]
        mock_response = _make_chat_completion_mock("Creative answer")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            await adapter.generate(messages, temperature=0.9, max_tokens=512)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.9
        assert call_kwargs.get("max_tokens") == 512

    @pytest.mark.asyncio
    async def test_generate_with_system_and_user_messages(self) -> None:
        """Given system + user messages, when generate() called, then both passed to API."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": "You are a bar assistant."},
            {"role": "user", "content": "What drinks do you have?"},
        ]
        mock_response = _make_chat_completion_mock("We have beer, wine, and cocktails.")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            result = await adapter.generate(messages)

        assert result == "We have beer, wine, and cocktails."
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"] == messages

    @pytest.mark.asyncio
    async def test_generate_raises_llm_error_on_exception(self) -> None:
        """Given API raises exception, when generate() called, then LLMError raised."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Hi"}]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            with pytest.raises(LLMError, match="API down"):
                await adapter.generate(messages)

    @pytest.mark.asyncio
    async def test_generate_llm_error_includes_provider(self) -> None:
        """Given API error, when LLMError raised, then provider field is 'openai_compatible'."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Hi"}]
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("fail"))

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            with pytest.raises(LLMError) as exc_info:
                await adapter.generate(messages)

        assert exc_info.value.provider == "openai_compatible"


# ============================================================================
# OpenAIAdapter — generate_with_tools()
# ============================================================================

class TestOpenAIAdapterGenerateWithTools:
    """RF-AI-14: generate_with_tools() includes tools in request and returns dict."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_includes_tools_param(self) -> None:
        """Given tools list, when generate_with_tools() called, then tools sent to API."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Book appointment"}]
        tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": "agendar_cita",
                    "description": "Agenda una cita",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        mock_response = _make_tool_call_response(content="Sure, let me book that.")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            await adapter.generate_with_tools(messages, tools)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["messages"] == messages

    @pytest.mark.asyncio
    async def test_generate_with_tools_returns_dict(self) -> None:
        """Given messages + tools, when generate_with_tools() called, then returns dict."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Help"}]
        tools: list[dict[str, Any]] = []
        mock_response = _make_tool_call_response(content="Response")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            result = await adapter.generate_with_tools(messages, tools)

        assert isinstance(result, dict)
        assert "content" in result

    @pytest.mark.asyncio
    async def test_generate_with_tools_returns_tool_calls(self) -> None:
        """Given LLM returns tool_calls, when generate_with_tools() called,
        then result dict includes tool_calls."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Agendar cita mañana 10am"}]
        tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {"name": "agendar_cita", "description": "Book appointment", "parameters": {}},
            }
        ]
        mock_response = _make_tool_call_response(
            content="",
            tool_calls=[
                {
                    "id": "call_abc123",
                    "function": {
                        "name": "agendar_cita",
                        "arguments": '{"input": "mañana 10am"}',
                    },
                }
            ],
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            result = await adapter.generate_with_tools(messages, tools)

        assert "tool_calls" in result
        assert len(result["tool_calls"]) >= 1

    @pytest.mark.asyncio
    async def test_generate_with_tools_passes_kwargs(self) -> None:
        """Given temperature kwarg, when generate_with_tools() called, then forwarded to API."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Hi"}]
        tools: list[dict[str, Any]] = []
        mock_response = _make_tool_call_response("Hi")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            await adapter.generate_with_tools(messages, tools, temperature=0.3, max_tokens=256)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.3
        assert call_kwargs.get("max_tokens") == 256

    @pytest.mark.asyncio
    async def test_generate_with_tools_raises_llm_error(self) -> None:
        """Given API error, when generate_with_tools() called, then LLMError raised."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Hi"}]
        tools: list[dict[str, Any]] = []
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("timeout"))

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(_make_settings())
            with pytest.raises(LLMError, match="timeout"):
                await adapter.generate_with_tools(messages, tools)


# ============================================================================
# OpenAIAdapter — OpenCode / Ollama compatibility
# ============================================================================

class TestOpenAIAdapterOpenCodeOllama:
    """RF-AI-03: Adapter works with any OpenAI-compatible API (OpenCode, Ollama)."""

    @pytest.mark.asyncio
    async def test_opencode_via_base_url(self) -> None:
        """Given base_url for OpenCode, when generate() called, then calls that URL."""
        settings = _make_settings(
            llm_api_key="sk-opencode-key",
            llm_base_url="https://orinoco.openco.de/v1",
            llm_model="opencode-model",
        )
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Test"}]
        mock_response = _make_chat_completion_mock("OpenCode response")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(settings)
            result = await adapter.generate(messages)

        assert result == "OpenCode response"

    @pytest.mark.asyncio
    async def test_ollama_via_base_url(self) -> None:
        """Given base_url for local Ollama, when generate() called, then calls localhost."""
        settings = _make_settings(
            llm_api_key="",  # Ollama does not require API key
            llm_base_url="http://localhost:11434/v1",
            llm_model="llama3",
        )
        messages: list[dict[str, Any]] = [{"role": "user", "content": "Test"}]
        mock_response = _make_chat_completion_mock("Ollama response")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.infrastructure.ai.openai_adapter.AsyncOpenAI", return_value=mock_client):
            adapter = OpenAIAdapter(settings)
            result = await adapter.generate(messages)

        assert result == "Ollama response"
