"""HTTP Router: Template endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.dtos import ApplyTemplateInput
from app.application.templates.apply_template import ApplyTemplateUseCase
from app.infrastructure.http.dependencies import (
    get_agent_repo,
    get_client_repo,
    get_template_service,
)
from app.infrastructure.http.schemas import (
    ApplyTemplateRequest,
    ApplyTemplateResponse,
    ClientResponse,
    TemplateItemSchema,
    TemplateListResponse,
    agent_output_to_response,
)
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository
from app.infrastructure.persistence.client_repository import SupabaseClientRepository
from app.infrastructure.templates.data import TemplateService

router = APIRouter()


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    service: TemplateService = Depends(get_template_service),
):
    """Lista todas las plantillas de servicio disponibles."""
    templates = service.list_templates()
    return TemplateListResponse(
        templates=[
            TemplateItemSchema(
                slug=t.slug,
                name=t.name,
                emoji=t.emoji,
                description=t.description,
                tools_count=len(t.agent_config.tools),
            )
            for t in templates
        ]
    )


@router.post("/{slug}/apply", response_model=ApplyTemplateResponse, status_code=201)
async def apply_template(
    slug: str,
    body: ApplyTemplateRequest,
    service: TemplateService = Depends(get_template_service),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
    agent_repo: SupabaseAgentRepository = Depends(get_agent_repo),
):
    """Aplica una plantilla: crea Cliente + Agente + Tools en 1 operación."""
    uc = ApplyTemplateUseCase(
        template_service=service,
        client_repo=client_repo,
        agent_repo=agent_repo,
    )
    output = await uc.execute(
        ApplyTemplateInput(
            slug=slug,
            name=body.name,
            whatsapp_number=body.whatsapp_number,
        )
    )
    return ApplyTemplateResponse(
        template_slug=output.template_slug,
        client=ClientResponse.model_validate(output.client),
        agent=agent_output_to_response(output.agent),
        message=output.message,
    )
