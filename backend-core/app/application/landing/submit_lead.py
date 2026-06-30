"""Procesa el envío de un formulario de landing page."""

from __future__ import annotations

from app.application.dtos import SubmitLandingInput, SubmitLandingOutput
from app.domain.agent.repository import AgentRepository
from app.domain.landing.repository import LandingRepository
from app.domain.lead.entity import Lead
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import (
    InvalidLeadError,
    LandingInactiveError,
    LandingNotFoundError,
    LandingRateLimitError,
)


class SubmitLandingLeadUseCase:
    """Procesa el envío de un formulario de landing page.

    Flujo:
    1. Buscar cliente por slug (LandingRepository)
    2. Validar landing activa y cliente activo
    3. Validar WhatsApp (mínimo 10 dígitos)
    4. Validar rate limit por IP (máximo 5 por minuto)
    5. Crear Lead con source="landing"
    6. Buscar agente activo del cliente
    7. Si hay agente: enviar WhatsApp con auto_reply (interpolando {{name}})
    8. Si no hay agente: continuar sin WhatsApp (degradación elegante)
    9. Retornar confirmación
    """

    def __init__(
        self,
        landing_repo: LandingRepository,
        lead_repo: LeadRepository,
        agent_repo: AgentRepository,
        message_sender=None,
    ) -> None:
        self._landing_repo = landing_repo
        self._lead_repo = lead_repo
        self._agent_repo = agent_repo
        self._message_sender = message_sender

    async def execute(
        self,
        input: SubmitLandingInput,
        client_ip: str = "0.0.0.0",
    ) -> SubmitLandingOutput:
        # 1. Buscar cliente por slug
        result = await self._landing_repo.find_client_by_slug(input.slug)
        if result is None:
            raise LandingNotFoundError(f"Landing page '{input.slug}' not found")

        client, landing_config = result

        # 2. Validar landing activa
        if not landing_config.is_active:
            raise LandingInactiveError("This landing page is not active")

        # 3. Validar cliente activo
        if not client.is_active:
            raise LandingInactiveError("This landing page is not available")

        # 4. Validar WhatsApp
        cleaned_phone = input.whatsapp.strip().replace("+", "").replace(" ", "").replace("-", "")
        if not cleaned_phone.isdigit() or len(cleaned_phone) < 10:
            raise InvalidLeadError("Invalid WhatsApp number: must be at least 10 digits")

        # 5. Validar nombre
        if not input.name.strip():
            raise InvalidLeadError("Name cannot be empty")

        # 6. Rate limiting por IP
        allowed = await self._landing_repo.check_rate_limit(client_ip, max_req=5, window_sec=60)
        if not allowed:
            raise LandingRateLimitError("Too many submissions. Please wait a minute and try again.")

        # 7. Crear Lead
        try:
            lead = Lead(
                client_id=client.id,
                phone=cleaned_phone,
                name=input.name.strip(),
                source="landing",
            )
        except ValueError as exc:
            raise InvalidLeadError(str(exc))

        await self._lead_repo.save(lead)

        # 8. Buscar agente activo del cliente
        agents = await self._agent_repo.find_active_by_client(client.id)

        # 9. Enviar WhatsApp si hay agente
        auto_reply = landing_config.auto_reply.replace("{{name}}", input.name.strip())
        if agents and self._message_sender is not None:
            agent = agents[0] if isinstance(agents, list) else agents
            try:
                await self._message_sender.send(
                    phone=cleaned_phone,
                    message=auto_reply,
                    agent_id=str(agent.id),
                )
            except Exception:
                pass

        # 10. Retornar
        return SubmitLandingOutput(
            lead_id=str(lead.id),
            message="¡Gracias! Te contactaremos pronto.",
            auto_reply=auto_reply,
        )
