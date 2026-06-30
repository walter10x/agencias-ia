"""Unit tests for LLMPort — Application Layer driving port (RED phase — TDD).

These tests define the contract that ALL LLM adapters must fulfill.
Imports from modules that do NOT exist yet — this is intentional.
"""

from __future__ import annotations

import abc
import inspect
from typing import Any

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.ports.llm_port import LLMPort, LLMError


# ============================================================================
# LLMPort — Abstract Base Class integrity
# ============================================================================

class TestLLMPortAbstract:
    """RF-AI-01: LLMPort is an abstract base class with generate() and generate_with_tools()."""

    def test_llm_port_is_abstract_class(self) -> None:
        """LLMPort must be an ABC so it cannot be instantiated directly."""
        assert issubclass(LLMPort, abc.ABC), "LLMPort must inherit from ABC"

    def test_cannot_instantiate_directly(self) -> None:
        """Given LLMPort is ABC, when instantiated, then TypeError is raised."""
        with pytest.raises(TypeError, match="abstract"):
            LLMPort()  # type: ignore[abstract]

    def test_generate_is_abstract_method(self) -> None:
        """generate() must be decorated with @abstractmethod."""
        assert hasattr(LLMPort, "generate"), "LLMPort must define generate"
        method = LLMPort.__dict__.get("generate")
        assert method is not None, "generate must be defined on LLMPort directly"
        assert hasattr(method, "__isabstractmethod__"), "generate must be abstract"

    def test_generate_with_tools_is_abstract_method(self) -> None:
        """generate_with_tools() must be decorated with @abstractmethod."""
        assert hasattr(LLMPort, "generate_with_tools"), "LLMPort must define generate_with_tools"
        method = LLMPort.__dict__.get("generate_with_tools")
        assert method is not None, "generate_with_tools must be defined on LLMPort directly"
        assert hasattr(method, "__isabstractmethod__"), "generate_with_tools must be abstract"


class TestLLMPortSignature:
    """Verify that the abstract methods have the correct signatures."""

    def test_generate_is_async(self) -> None:
        """generate() must be coroutine (async def)."""
        method = LLMPort.__dict__.get("generate")
        assert method is not None
        assert inspect.iscoroutinefunction(method), "generate() must be async def"

    def test_generate_accepts_messages_list(self) -> None:
        """generate() must accept messages: list[dict[str, Any]] as first parameter."""
        sig = inspect.signature(LLMPort.generate)
        params = list(sig.parameters.keys())
        assert "self" in params or "messages" in params, "generate must have 'messages' parameter"
        assert "messages" in params, "generate() must accept messages parameter"

    def test_generate_accepts_kwargs(self) -> None:
        """generate() must accept **kwargs for provider-specific parameters."""
        sig = inspect.signature(LLMPort.generate)
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        assert has_kwargs, "generate() must accept **kwargs"

    def test_generate_returns_str(self) -> None:
        """generate() return annotation must be str."""
        sig = inspect.signature(LLMPort.generate)
        assert sig.return_annotation is str, "generate() must return str"

    def test_generate_with_tools_is_async(self) -> None:
        """generate_with_tools() must be coroutine (async def)."""
        method = LLMPort.__dict__.get("generate_with_tools")
        assert method is not None
        assert inspect.iscoroutinefunction(method), "generate_with_tools() must be async def"

    def test_generate_with_tools_accepts_messages_and_tools(self) -> None:
        """generate_with_tools() must accept messages and tools params."""
        sig = inspect.signature(LLMPort.generate_with_tools)
        params = list(sig.parameters.keys())
        assert "messages" in params, "generate_with_tools() must accept 'messages'"
        assert "tools" in params, "generate_with_tools() must accept 'tools'"

    def test_generate_with_tools_accepts_kwargs(self) -> None:
        """generate_with_tools() must accept **kwargs."""
        sig = inspect.signature(LLMPort.generate_with_tools)
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        assert has_kwargs, "generate_with_tools() must accept **kwargs"

    def test_generate_with_tools_returns_dict(self) -> None:
        """generate_with_tools() return annotation must be dict[str, Any]."""
        sig = inspect.signature(LLMPort.generate_with_tools)
        annotation_str = str(sig.return_annotation)
        assert "dict" in annotation_str, (
            f"generate_with_tools() must return dict, got {annotation_str}"
        )


class TestConcreteImplementationRequired:
    """Any concrete subclass MUST implement both abstract methods."""

    def test_subclass_missing_generate_fails(self) -> None:
        """When subclass omits generate(), instantiation raises TypeError."""
        class BadAdapter(LLMPort):
            async def generate_with_tools(
                self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], **kwargs: Any
            ) -> dict[str, Any]:
                return {"content": "stub"}

        with pytest.raises(TypeError, match="abstract"):
            BadAdapter()  # type: ignore[abstract]

    def test_subclass_missing_generate_with_tools_fails(self) -> None:
        """When subclass omits generate_with_tools(), instantiation raises TypeError."""
        class BadAdapter(LLMPort):
            async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
                return "stub"

        with pytest.raises(TypeError, match="abstract"):
            BadAdapter()  # type: ignore[abstract]

    def test_subclass_implementing_both_succeeds(self) -> None:
        """When subclass implements both methods, instantiation succeeds."""
        class GoodAdapter(LLMPort):
            async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
                return "ok"

            async def generate_with_tools(
                self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], **kwargs: Any
            ) -> dict[str, Any]:
                return {"content": "ok"}

        adapter = GoodAdapter()
        assert isinstance(adapter, LLMPort)


# ============================================================================
# LLMError — Domain error for the LLM port
# ============================================================================

class TestLLMError:
    """RF-AI-01 (error): LLMError carries provider info and status code."""

    def test_creates_with_message_only(self) -> None:
        """Given a message string, when LLMError created, then message stored."""
        error = LLMError("Something went wrong")
        assert error.message == "Something went wrong"
        assert str(error) == "Something went wrong"

    def test_creates_with_provider_and_status(self) -> None:
        """Given message, provider, status_code, when LLMError created, then all stored."""
        error = LLMError(
            message="Rate limit exceeded",
            provider="openai",
            status_code=429,
        )
        assert error.message == "Rate limit exceeded"
        assert error.provider == "openai"
        assert error.status_code == 429

    def test_is_exception_subclass(self) -> None:
        """LLMError must inherit from Exception."""
        assert issubclass(LLMError, Exception)

    def test_default_provider_is_empty_string(self) -> None:
        """Given no provider, when LLMError created, then provider defaults to ''."""
        error = LLMError("Timeout")
        assert error.provider == ""

    def test_default_status_code_is_zero(self) -> None:
        """Given no status_code, when LLMError created, then status_code defaults to 0."""
        error = LLMError("Error")
        assert error.status_code == 0
