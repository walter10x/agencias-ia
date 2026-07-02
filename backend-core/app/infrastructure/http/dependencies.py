"""FastAPI dependency factories for repositories, security, and auth."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.auth.get_current_client import GetCurrentClientUseCase
from app.application.dtos import CurrentClientOutput
from app.domain.shared.errors import AuthError, UnauthorizedError
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.http.supabase_client import SupabaseHttpClient
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository
from app.infrastructure.persistence.client_repository import SupabaseClientRepository
from app.infrastructure.persistence.conversation_repository import SupabaseConversationRepository
from app.infrastructure.security.jwt_handler import JoseJwtHandler
from app.infrastructure.security.password_hasher import BcryptPasswordHasher

_security = HTTPBearer(auto_error=False)


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


# ============================================================================
# Auth dependencies
# ============================================================================


def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


def get_jwt_handler(settings: Settings = Depends(get_settings)) -> JoseJwtHandler:
    return JoseJwtHandler(settings)


async def get_current_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    repo: SupabaseClientRepository = Depends(get_client_repo),
    jwt_handler: JoseJwtHandler = Depends(get_jwt_handler),
) -> CurrentClientOutput:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt_handler.decode(credentials.credentials)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    client_id = payload.get("client_id")
    if client_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    uc = GetCurrentClientUseCase(repo)
    try:
        return await uc.execute(client_id)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


async def require_superadmin(
    current: CurrentClientOutput = Depends(get_current_client),
) -> CurrentClientOutput:
    if current.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current
