"""Actualiza la configuración de landing page de un cliente (admin)."""

from __future__ import annotations

from app.application.dtos import LandingConfigOutput, UpdateLandingConfigInput
from app.domain.landing.repository import LandingRepository
from app.domain.shared.slugify import generate_unique_slug
from app.domain.shared.value_objects import LandingSlug


class UpdateLandingConfigUseCase:
    """Actualiza la configuración de landing page de un cliente (admin).

    Flujo:
    1. Validar que al menos un campo fue proporcionado (DTO lo hace)
    2. Si se proporciona slug, validar formato y unicidad
    3. Si slug duplicado, auto-generar sufijo numérico
    4. Si se activa landing sin slug, auto-generar del nombre del cliente
    5. Guardar cambios
    """

    def __init__(self, landing_repo: LandingRepository) -> None:
        self._landing_repo = landing_repo

    async def execute(self, input: UpdateLandingConfigInput) -> LandingConfigOutput:
        # 1. Si se proporciona slug
        if input.landing_slug is not None:
            slug = LandingSlug(input.landing_slug.strip())

            # Verificar unicidad (excluyendo el propio cliente)
            exists = await self._landing_repo.slug_exists(
                str(slug),
                exclude_client_id=input.client_id,
            )
            if exists:
                existing = await self._landing_repo.get_all_slugs()
                new_slug = generate_unique_slug(str(slug), existing)
                object.__setattr__(input, "landing_slug", new_slug)
            else:
                object.__setattr__(input, "landing_slug", str(slug))

        # 2. Si se activa la landing y no tiene slug, auto-generar del nombre del cliente
        if input.landing_active is True:
            if input.landing_slug is None:
                current = await self._landing_repo.get_landing_config(input.client_id)
                if current is not None and not current.slug:
                    client = await self._landing_repo.get_client(input.client_id)
                    if client is not None:
                        existing = await self._landing_repo.get_all_slugs()
                        new_slug = generate_unique_slug(client.name, existing)
                        object.__setattr__(input, "landing_slug", new_slug)

        # 3. Guardar
        config = await self._landing_repo.update_landing_config(
            client_id=input.client_id,
            data=input,
        )

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
