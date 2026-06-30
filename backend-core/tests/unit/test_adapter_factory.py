"""Unit tests for AdapterFactory — LLM adapter selection and caching (RED phase — TDD).

Tests the factory that returns the correct LLMPort implementation
based on settings.llm_provider, with singleton caching.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.ports.llm_port import LLMPort

# --- Infrastructure layer (does NOT exist yet — RED phase) ---
from app.infrastructure.ai.adapter_factory import get_llm_adapter
from app.infrastructure.ai.openai_adapter import OpenAIAdapter
from app.infrastructure.config.settings import Settings


# ============================================================================
# Helpers
# ============================================================================

def _make_settings(**overrides: Any) -> Settings:
    """Build a Settings instance with LLM fields for testing."""
    return Settings(
        llm_provider=str(overrides.get("llm_provider", "openai")),
        llm_api_key=str(overrides.get("llm_api_key", "sk-test-key")),
        llm_base_url=str(overrides.get("llm_base_url", "")),
        llm_model=str(overrides.get("llm_model", "gpt-4o-mini")),
    )


# ============================================================================
# get_llm_adapter() — Provider Selection
# ============================================================================

class TestAdapterFactoryProviderSelection:
    """RF-AI-06: Factory returns correct adapter based on llm_provider."""

    def test_openai_provider_returns_openai_adapter(self) -> None:
        """Given llm_provider='openai', when get_llm_adapter() called, then returns OpenAIAdapter."""
        settings = _make_settings(llm_provider="openai")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)
            assert isinstance(adapter, LLMPort)

    def test_opencode_provider_returns_openai_adapter(self) -> None:
        """Given llm_provider='opencode', when get_llm_adapter() called, then returns OpenAIAdapter."""
        settings = _make_settings(
            llm_provider="opencode",
            llm_base_url="https://orinoco.openco.de/v1",
        )
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)

    def test_ollama_provider_returns_openai_adapter(self) -> None:
        """Given llm_provider='ollama', when get_llm_adapter() called, then returns OpenAIAdapter."""
        settings = _make_settings(
            llm_provider="ollama",
            llm_api_key="",
            llm_base_url="http://localhost:11434/v1",
        )
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)

    def test_case_insensitive_provider(self) -> None:
        """Given llm_provider='OPENAI' (uppercase), when get_llm_adapter() called,
        then still returns OpenAIAdapter (case-insensitive)."""
        settings = _make_settings(llm_provider="OPENAI")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)

    def test_opencode_mixed_case(self) -> None:
        """Given llm_provider='OpenCode' (mixed case), when get_llm_adapter() called,
        then returns OpenAIAdapter."""
        settings = _make_settings(
            llm_provider="OpenCode",
            llm_base_url="https://orinoco.openco.de/v1",
        )
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)


# ============================================================================
# get_llm_adapter() — Unknown Provider
# ============================================================================

class TestAdapterFactoryUnknownProvider:
    """RF-AI-06 (error): Factory raises ValueError for unsupported providers."""

    def test_raises_value_error_for_unknown_provider(self) -> None:
        """Given llm_provider='unknown_llm', when get_llm_adapter() called,
        then raises ValueError."""
        settings = _make_settings(llm_provider="unknown_llm")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                get_llm_adapter()

    def test_raises_for_empty_provider(self) -> None:
        """Given llm_provider='', when get_llm_adapter() called,
        then raises ValueError (empty string is not a valid provider)."""
        settings = _make_settings(llm_provider="")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                get_llm_adapter()

    def test_error_message_includes_provider_name(self) -> None:
        """Given unknown provider, when ValueError raised, then message contains the provider name."""
        settings = _make_settings(llm_provider="gemini")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            with pytest.raises(ValueError) as exc_info:
                get_llm_adapter()
            assert "gemini" in str(exc_info.value)


# ============================================================================
# get_llm_adapter() — Singleton Caching
# ============================================================================

class TestAdapterFactorySingletonCaching:
    """NFR-AI-06: Factory caches the adapter instance (singleton) using lru_cache."""

    def test_returns_same_instance_on_multiple_calls(self) -> None:
        """Given same provider, when get_llm_adapter() called twice,
        then returns the same object instance."""
        settings = _make_settings(llm_provider="openai")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            # Clear the cache before testing cache behavior
            get_llm_adapter.cache_clear()  # type: ignore[attr-defined]
            adapter1 = get_llm_adapter()
            adapter2 = get_llm_adapter()
            assert adapter1 is adapter2

    def test_cache_respects_provider_change(self) -> None:
        """Given cache cleared between provider changes, when get_llm_adapter() called,
        then different instances for different providers (cache should clear on settings change)."""
        # Note: lru_cache caches based on function arguments.
        # Since get_llm_adapter() has no arguments, the cache key is always the same.
        # In production, the adapter is created once at startup.
        # This test verifies that clearing cache + new settings = new instance.
        settings_openai = _make_settings(llm_provider="openai")
        settings_opencode = _make_settings(
            llm_provider="opencode",
            llm_base_url="https://orinoco.openco.de/v1",
        )

        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            side_effect=[settings_openai, settings_opencode],
        ):
            get_llm_adapter.cache_clear()  # type: ignore[attr-defined]
            adapter1 = get_llm_adapter()
            get_llm_adapter.cache_clear()  # type: ignore[attr-defined]
            adapter2 = get_llm_adapter()
            # Both are OpenAIAdapter but created with different settings
            assert isinstance(adapter1, OpenAIAdapter)
            assert isinstance(adapter2, OpenAIAdapter)
            assert adapter1._model == "gpt-4o-mini"

    def test_lru_cache_is_used(self) -> None:
        """Verify that get_llm_adapter is decorated with lru_cache."""
        assert hasattr(get_llm_adapter, "cache_clear"), (
            "get_llm_adapter must use @lru_cache for singleton caching"
        )
        assert hasattr(get_llm_adapter, "cache_info"), (
            "get_llm_adapter must use @lru_cache"
        )


# ============================================================================
# get_llm_adapter() — Integration with Settings
# ============================================================================

class TestAdapterFactorySettingsIntegration:
    """Factory reads settings.get_settings() to determine provider."""

    def test_reads_provider_from_settings(self) -> None:
        """Given settings.llm_provider='openai', when factory called,
        then get_settings() is invoked."""
        settings = _make_settings(llm_provider="openai")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ) as mock_get_settings:
            get_llm_adapter.cache_clear()  # type: ignore[attr-defined]
            get_llm_adapter()
            mock_get_settings.assert_called_once()

    def test_returns_llm_port_type(self) -> None:
        """Given any valid provider, when get_llm_adapter() called,
        then returned object is an instance of LLMPort."""
        settings = _make_settings(llm_provider="openai")
        with patch(
            "app.infrastructure.ai.adapter_factory.get_settings",
            return_value=settings,
        ):
            get_llm_adapter.cache_clear()  # type: ignore[attr-defined]
            adapter = get_llm_adapter()
            assert isinstance(adapter, LLMPort)
