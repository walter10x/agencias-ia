"""Factory que devuelve el adaptador LLM correcto según settings."""

from __future__ import annotations

from app.application.ports.llm_port import LLMPort
from app.infrastructure.config.settings import get_settings


_cached_adapter: LLMPort | None = None
_last_provider: str = ""


def get_llm_adapter() -> LLMPort:
    """Devuelve el adaptador LLM según settings.llm_provider.

    El resultado se cachea (singleton) para reutilizar la conexión HTTP.
    Se revalida si cambia el provider.

    Returns:
        Instancia concreta de LLMPort.

    Raises:
        ValueError: Si llm_provider no es soportado.
    """
    global _cached_adapter, _last_provider

    settings = get_settings()
    provider = settings.llm_provider.lower()

    # Return cached adapter if provider hasn't changed
    if _cached_adapter is not None and _last_provider == provider:
        return _cached_adapter

    if provider in ("openai", "opencode", "ollama"):
        from app.infrastructure.ai.openai_adapter import OpenAIAdapter
        _cached_adapter = OpenAIAdapter(settings)
        _last_provider = provider
        return _cached_adapter

    raise ValueError(f"Unsupported LLM provider: {provider}")


def _cache_clear() -> None:
    """Clear the adapter cache."""
    global _cached_adapter, _last_provider
    _cached_adapter = None
    _last_provider = ""


# Expose lru_cache-like interface for test compatibility
get_llm_adapter.cache_clear = _cache_clear  # type: ignore[attr-defined]
get_llm_adapter.cache_info = lambda: None  # type: ignore[attr-defined]
