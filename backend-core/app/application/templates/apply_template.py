"""Caso de uso: aplicar una plantilla de servicio.

Crea Cliente + Agente + Tools en 1 operación.
"""

from __future__ import annotations

from app.application.dtos import (
    ApplyTemplateInput,
    ApplyTemplateOutput,
    client_to_output,
    agent_to_output,
)
from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import InvalidTemplateError
from app.domain.shared.value_objects import BusinessType, WhatsAppNumber
from app.infrastructure.templates.data import TemplateService


class ApplyTemplateUseCase:
    """Aplica una plantilla: crea Cliente + Agente + Tools en 1 operación.

    Flujo:
    1. Valida slug de plantilla
    2. Recupera TemplateDef del TemplateService
    3. Crea Client con business_type y whatsapp_number
    4. Crea Agent con personality y tools de la plantilla
    5. Retorna ambos en ApplyTemplateOutput
    """

    def __init__(
        self,
        template_service: TemplateService,
        client_repo: ClientRepository,
        agent_repo: AgentRepository,
    ) -> None:
        self._template_service = template_service
        self._client_repo = client_repo
        self._agent_repo = agent_repo

    async def execute(self, input: ApplyTemplateInput) -> ApplyTemplateOutput:
        # 1. Validar slug
        if not input.slug.strip():
            raise InvalidTemplateError("Template slug is required")
        if not input.name.strip():
            raise InvalidTemplateError("Client name cannot be empty")

        # 2. Obtener plantilla
        template = self._template_service.get_template(input.slug)

        # 3. Crear Client
        client = Client(
            name=input.name.strip(),
            business_type=BusinessType(template.client_config.business_type),
            whatsapp_number=WhatsAppNumber(input.whatsapp_number),
        )
        await self._client_repo.save(client)

        # 4. Crear Agent
        tools = [
            AgentTool(name=t.name, description=t.description, endpoint=t.endpoint)
            for t in template.agent_config.tools
        ]
        agent = Agent(
            client_id=client.id,
            name=f"Asistente {template.name}",
            personality=template.agent_config.personality,
            tools=tools,
        )
        await self._agent_repo.save(agent)

        # 5. Retornar
        return ApplyTemplateOutput(
            template_slug=template.slug,
            client=client_to_output(client),
            agent=agent_to_output(agent),
            message="Plantilla aplicada correctamente. Cliente y agente creados.",
        )
