"""HTTP Router: Landing page endpoints (public + admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.application.dtos import (
    GetLandingConfigInput,
    SubmitLandingInput,
    UpdateLandingConfigInput,
)
from app.application.landing.get_landing_config import GetLandingConfigUseCase
from app.application.landing.submit_lead import SubmitLandingLeadUseCase
from app.application.landing.update_landing_config import UpdateLandingConfigUseCase
from app.domain.shared.errors import LandingInactiveError, LandingNotFoundError
from app.infrastructure.http.dependencies import (
    get_agent_repo,
    get_landing_repo,
    get_lead_repo,
)
from app.infrastructure.http.schemas import (
    LandingConfigResponse,
    LandingPublicConfigResponse,
    LandingSubmitRequest,
    LandingSubmitResponse,
    LandingUpdateRequest,
)
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository
from app.infrastructure.persistence.landing_repository import SupabaseLandingRepository
from app.infrastructure.persistence.lead_repository import SupabaseLeadRepository

public_router = APIRouter()
admin_router = APIRouter()


# ============================================================================
# Endpoints públicos (sin auth)
# ============================================================================


@public_router.get("/{slug}/config", response_model=LandingPublicConfigResponse)
async def get_landing_public_config(
    slug: str,
    landing_repo: SupabaseLandingRepository = Depends(get_landing_repo),
):
    """Obtiene la configuración pública de la landing page."""
    result = await landing_repo.find_client_by_slug(slug)
    if result is None:
        raise LandingNotFoundError(f"Landing page '{slug}' not found")

    client, config = result
    if not config.is_active or not client.is_active:
        raise LandingInactiveError("This landing page is not active")

    return LandingPublicConfigResponse(
        client_name=client.name,
        landing_title=config.title,
        landing_description=config.description,
        landing_active=config.is_active,
        landing_primary_color=config.primary_color,
    )


@public_router.post("/{slug}/submit", response_model=LandingSubmitResponse, status_code=201)
async def submit_landing_form(
    slug: str,
    body: LandingSubmitRequest,
    request: Request,
    landing_repo: SupabaseLandingRepository = Depends(get_landing_repo),
    lead_repo: SupabaseLeadRepository = Depends(get_lead_repo),
    agent_repo: SupabaseAgentRepository = Depends(get_agent_repo),
):
    """Endpoint público: envía el formulario de la landing page."""
    client_ip = request.client.host if request.client else "0.0.0.0"

    uc = SubmitLandingLeadUseCase(
        landing_repo=landing_repo,
        lead_repo=lead_repo,
        agent_repo=agent_repo,
        message_sender=None,
    )
    output = await uc.execute(
        SubmitLandingInput(
            slug=slug,
            name=body.name,
            whatsapp=body.whatsapp,
            interest=body.interest,
        ),
        client_ip=client_ip,
    )
    return LandingSubmitResponse(
        lead_id=output.lead_id,
        message=output.message,
        auto_reply=output.auto_reply,
    )


# ============================================================================
# Endpoints admin (bajo /clients/{id}/landing)
# ============================================================================


@admin_router.get("/{client_id}/landing", response_model=LandingConfigResponse)
async def get_landing_config(
    client_id: str,
    landing_repo: SupabaseLandingRepository = Depends(get_landing_repo),
):
    """Obtiene la configuración completa de landing de un cliente (admin)."""
    uc = GetLandingConfigUseCase(landing_repo=landing_repo)
    output = await uc.execute(GetLandingConfigInput(client_id=client_id))
    return LandingConfigResponse(
        client_id=output.client_id,
        landing_slug=output.landing_slug,
        landing_title=output.landing_title,
        landing_description=output.landing_description,
        landing_active=output.landing_active,
        landing_primary_color=output.landing_primary_color,
        landing_auto_reply=output.landing_auto_reply,
        leads_count=output.leads_count,
    )


@admin_router.patch("/{client_id}/landing", response_model=LandingConfigResponse)
async def update_landing_config(
    client_id: str,
    body: LandingUpdateRequest,
    landing_repo: SupabaseLandingRepository = Depends(get_landing_repo),
):
    """Actualiza la configuración de landing de un cliente (admin)."""
    uc = UpdateLandingConfigUseCase(landing_repo=landing_repo)
    output = await uc.execute(
        UpdateLandingConfigInput(
            client_id=client_id,
            landing_slug=body.landing_slug,
            landing_title=body.landing_title,
            landing_description=body.landing_description,
            landing_active=body.landing_active,
            landing_primary_color=body.landing_primary_color,
            landing_auto_reply=body.landing_auto_reply,
        )
    )
    return LandingConfigResponse(
        client_id=output.client_id,
        landing_slug=output.landing_slug,
        landing_title=output.landing_title,
        landing_description=output.landing_description,
        landing_active=output.landing_active,
        landing_primary_color=output.landing_primary_color,
        landing_auto_reply=output.landing_auto_reply,
        leads_count=output.leads_count,
    )
