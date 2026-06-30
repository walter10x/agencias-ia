"""Obtiene la configuración de landing page de un cliente (admin)."""

from __future__ import annotations

from app.application.dtos import GetLandingConfigInput, LandingConfigOutput
from app.domain.landing.repository import LandingRepository
from app.domain.shared.errors import ClientNotFoundError


class GetLandingConfigUseCase:
    """Obtiene la configuración de landing page de un cliente (admin)."""

    def __init__(self, landing_repo: LandingRepository) -> None:
        self._landing_repo = landing_repo

    async def execute(self, input: GetLandingConfigInput) -> LandingConfigOutput:
        config = await self._landing_repo.get_landing_config(input.client_id)
        if config is None:
            raise ClientNotFoundError(f"Client '{input.client_id}' not found")

        leads_count = await self._landing_repo.count_leads_by_landing(input.client_id)

        return LandingConfigOutput(
            client_id=config.client_id,
            landing_slug=config.slug if config.slug else None,
            landing_title=config.title,
            landing_description=config.description,
            landing_active=config.is_active,
            landing_primary_color=config.primary_color,
            landing_auto_reply=config.auto_reply,
            leads_count=leads_count,
        )
