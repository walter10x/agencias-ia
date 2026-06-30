"""Tareas asíncronas de Celery.

La tarea process_whatsapp_message es el ORQUESTADOR PRINCIPAL
que conecta todos los componentes de la capa de IA.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from celery.utils.log import get_task_logger

from app.application.ports.llm_port import LLMError
from app.domain.agent.entity import Agent
from app.domain.agent.repository import AgentRepository
from app.domain.shared.value_objects import AgentId
from app.infrastructure.ai.adapter_factory import get_llm_adapter
from app.infrastructure.ai.agent_graph import run_agent
from app.infrastructure.ai.prompts import build_system_prompt, build_user_message
from app.infrastructure.ai.tools import agent_tools_to_openai_format
from app.infrastructure.config.celery_app import celery_app
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository

logger = get_task_logger(__name__)


@celery_app.task(
    name="process_whatsapp_message",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(LLMError,),
)
def process_whatsapp_message(
    self,
    client_id: str,
    phone: str,
    message: str,
    agent_id: str = "",
    push_name: str = "",
) -> dict:
    """Procesa un mensaje de WhatsApp con el agente IA.

    Flujo completo:
    1. Cargar agente desde Supabase
    2. (Futuro) Cargar historial de conversación
    3. Construir system prompt
    4. Convertir tools
    5. Ejecutar LangGraph agent
        6. Enviar respuesta vía WhatsApp client interno
    7. (Futuro) Guardar mensaje + respuesta en DB

    Args:
        client_id: ID del cliente (negocio) propietario del agente.
        phone: Número de WhatsApp del remitente.
        message: Contenido del mensaje sanitizado.
        agent_id: ID del agente IA que procesa el mensaje.
        push_name: Nombre público del usuario en WhatsApp.

    Returns:
        dict con status y respuesta generada.
    """
    settings = get_settings()

    try:
        # --- Paso 1: Cargar agente ---
        agent = _load_agent_sync(agent_id)
        if agent is None:
            logger.error(f"Agent not found: {agent_id}")
            return {"status": "error", "reason": "agent_not_found"}

        # --- Paso 2: Obtener LLM adapter ---
        llm = get_llm_adapter()

        # --- Paso 3: Construir system prompt ---
        system_prompt = build_system_prompt(agent)

        # --- Paso 4: Convertir tools ---
        tools = agent_tools_to_openai_format(agent.tools)

        # --- Paso 5: Preparar contexto ---
        agent_config = {
            "id": str(agent.id),
            "name": agent.name,
        }
        client_context = {
            "id": client_id,
        }
        user_message = build_user_message(phone, message, push_name)

        # --- Paso 6: Ejecutar LangGraph Agent ---
        loop = asyncio.new_event_loop()
        try:
            reply = loop.run_until_complete(
                run_agent(
                    llm=llm,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    agent_config=agent_config,
                    client_context=client_context,
                    tools=tools,
                )
            )
        finally:
            loop.close()

        # --- Paso 7: Enviar respuesta vía WhatsApp client interno ---
        _send_whatsapp_message(phone, reply, settings)

        # --- Paso 8: Guardar en DB (stub) ---
        logger.info(f"Message processed. Agent={agent.name} Phone={phone[:4]}...")

        return {"status": "sent", "reply": reply[:200]}

    except LLMError as e:
        logger.error(f"LLM error: {e.message} (provider={e.provider})")
        raise  # Celery retry

    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}")
        return {"status": "error", "reason": str(e)[:200]}


def _load_agent_sync(agent_id: str) -> Agent | None:
    """Carga un agente desde Supabase de forma síncrona (Celery no es async)."""
    settings = get_settings()
    from app.infrastructure.http.supabase_client import SupabaseHttpClient

    client = SupabaseHttpClient(settings.supabase_url, settings.supabase_service_key)
    repo = SupabaseAgentRepository(client)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            repo.find_by_id(AgentId(UUID(agent_id)))
        )
    finally:
        loop.close()


def _send_whatsapp_message(phone: str, text: str, settings) -> bool:
    """Send WhatsApp message via Meta Cloud API."""
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        logger.warning("[WHATSAPP] Meta not configured — message logged only")
        logger.info(f"[WHATSAPP] To: {phone} | {text[:100]}")
        return True

    import httpx
    try:
        url = (
            f"https://graph.facebook.com/{settings.whatsapp_api_version}"
            f"/{settings.whatsapp_phone_number_id}/messages"
        )
        resp = httpx.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "text": {"body": text},
            },
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            timeout=10,
        )
        if resp.is_success:
            logger.info(f"[WHATSAPP] Sent to {phone}")
            return True
        else:
            logger.error(f"[WHATSAPP] Failed: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"[WHATSAPP] Error: {e}")
        return False
