"""FastAPI dependency factories for repositories and external clients."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from app.infrastructure.config.settings import get_settings
from app.infrastructure.http.supabase_client import SupabaseHttpClient
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository
from app.infrastructure.persistence.client_repository import SupabaseClientRepository
from app.infrastructure.persistence.conversation_repository import SupabaseConversationRepository


@lru_cache
def _get_supabase_client() -> SupabaseHttpClient:
    """Singleton Supabase HTTP client."""
    settings = get_settings()
    return SupabaseHttpClient(
        url=settings.supabase_url,
        key=settings.supabase_service_key,
    )


def get_client_repo(
    client: SupabaseHttpClient = Depends(_get_supabase_client),
) -> SupabaseClientRepository:
    return SupabaseClientRepository(client)


def get_agent_repo(
    client: SupabaseHttpClient = Depends(_get_supabase_client),
) -> SupabaseAgentRepository:
    return SupabaseAgentRepository(client)


def get_conversation_repo(
    client: SupabaseHttpClient = Depends(_get_supabase_client),
) -> SupabaseConversationRepository:
    """FastAPI dependency: yields a SupabaseConversationRepository."""
    return SupabaseConversationRepository(client)


def get_lead_repo(
    client: SupabaseHttpClient = Depends(_get_supabase_client),
) -> "SupabaseLeadRepository":
    from app.infrastructure.persistence.lead_repository import SupabaseLeadRepository
    return SupabaseLeadRepository(client)


def get_template_service() -> "TemplateService":
    """FastAPI dependency: yields a TemplateService singleton."""
    from app.infrastructure.templates.data import TemplateService
    return TemplateService()


def get_feedback_repo(
    client: SupabaseHttpClient = Depends(_get_supabase_client),
) -> "SupabaseFeedbackRepository":
    from app.infrastructure.persistence.feedback_repository import SupabaseFeedbackRepository
    return SupabaseFeedbackRepository(client)


def get_landing_repo(
    client: SupabaseHttpClient = Depends(_get_supabase_client),
) -> "SupabaseLandingRepository":
    from app.infrastructure.persistence.landing_repository import SupabaseLandingRepository
    return SupabaseLandingRepository(client)


def get_email_repo(
    client: SupabaseHttpClient = Depends(_get_supabase_client),
) -> "SupabaseEmailRepository":
    from app.infrastructure.persistence.email_repository import SupabaseEmailRepository
    return SupabaseEmailRepository(client)
