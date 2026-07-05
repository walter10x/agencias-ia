"""Tareas asíncronas de Celery.

La tarea process_whatsapp_message es el ORQUESTADOR PRINCIPAL
que conecta todos los componentes de la capa de IA.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from celery.utils.log import get_task_logger

from app.application.ports.llm_port import LLMError
from app.domain.agent.entity import Agent
from app.domain.conversation.entity import Conversation, Message
from app.domain.conversation.repository import ConversationRepository
from app.domain.shared.errors import DomainError
from app.domain.shared.value_objects import AgentId
from app.infrastructure.ai.adapter_factory import get_llm_adapter
from app.infrastructure.ai.agent_graph import run_agent
from app.infrastructure.ai.prompts import build_system_prompt, build_user_message
from app.infrastructure.ai.tools import agent_tools_to_openai_format
from app.infrastructure.config.celery_app import celery_app
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository
from app.infrastructure.persistence.conversation_repository import (
    SupabaseConversationRepository,
)
from app.infrastructure.whatsapp.sender import WhatsAppSender

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
    2. Construir system prompt + tools
    3. Buscar/crear conversación por (client_id, phone), guardar el
       mensaje entrante y cargar los últimos N mensajes como historial
    4. Ejecutar LangGraph agent (historial inyectado como mensajes de chat)
    5. Enviar respuesta vía Meta Cloud API
    6. Guardar la respuesta del agente con el estado real del envío
       (sent / failed / skipped)

    Args:
        client_id: ID del cliente (negocio) propietario del agente.
        phone: Número de WhatsApp del remitente.
        message: Contenido del mensaje sanitizado.
        agent_id: ID del agente IA que procesa el mensaje.
        push_name: Nombre público del usuario en WhatsApp.

    Returns:
        dict con status (sent/failed/skipped/error), respuesta generada
        y conversation_id (si la persistencia estuvo disponible).
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

        # --- Paso 6: Persistir mensaje entrante + cargar historial ---
        # Best-effort: si la BD falla, se responde igualmente sin memoria.
        conversation, history = _persist_incoming_message_sync(
            client_id=client_id,
            phone=phone,
            content=message,
            agent_id=str(agent.id),
            history_limit=settings.conversation_history_limit,
        )

        # --- Paso 7: Ejecutar LangGraph Agent ---
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
                    history=history,
                )
            )
        finally:
            loop.close()

        # --- Paso 8: Enviar respuesta vía WhatsApp (Meta Cloud API) ---
        send_status = _send_whatsapp_message(client_id, phone, reply, settings)

        # --- Paso 9: Guardar respuesta con estado real del envío ---
        if conversation is not None:
            _persist_agent_reply_sync(conversation, reply, send_status)

        logger.info(
            f"Message processed. Agent={agent.name} Phone={phone[:4]}... "
            f"send_status={send_status}"
        )

        return {
            "status": send_status,
            "reply": reply[:200],
            "conversation_id": str(conversation.id) if conversation else None,
        }

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


def _get_conversation_repo() -> ConversationRepository:
    """Construye el repositorio de conversaciones (adaptador Supabase)."""
    settings = get_settings()
    from app.infrastructure.http.supabase_client import SupabaseHttpClient

    client = SupabaseHttpClient(settings.supabase_url, settings.supabase_service_key)
    return SupabaseConversationRepository(client)


def _persist_incoming_message_sync(
    client_id: str,
    phone: str,
    content: str,
    agent_id: str,
    history_limit: int,
) -> tuple[Conversation | None, list[dict]]:
    """Busca/crea la conversación, carga historial y guarda el mensaje entrante.

    Best-effort: si la persistencia falla, se loguea el error y se
    devuelve (None, []) para no bloquear la respuesta al usuario.

    Returns:
        (conversation, history) donde history son los últimos N mensajes
        PREVIOS al entrante, como dicts {"role", "content"} listos para
        inyectar en el chat del LLM.
    """
    try:
        repo = _get_conversation_repo()
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                _persist_incoming_message(
                    repo, client_id, phone, content, agent_id, history_limit
                )
            )
        finally:
            loop.close()
    except (DomainError, ValueError) as e:
        logger.error(f"[PERSISTENCE] Could not persist incoming message: {e}")
        return None, []


async def _persist_incoming_message(
    repo: ConversationRepository,
    client_id: str,
    phone: str,
    content: str,
    agent_id: str,
    history_limit: int,
) -> tuple[Conversation, list[dict]]:
    """Lógica async de persistencia del mensaje entrante + historial."""
    conversation = await repo.find_by_client_and_phone(client_id, phone)
    if conversation is None:
        conversation = Conversation(
            client_id=UUID(client_id),
            agent_id=UUID(agent_id) if agent_id else None,
            wa_phone_number=phone,
        )
        logger.info(
            f"[PERSISTENCE] New conversation {conversation.id} "
            f"(client={client_id}, phone={phone[:4]}...)"
        )
    else:
        conversation.updated_at = datetime.now(timezone.utc)

    # Upsert: crea la conversación nueva o refresca updated_at de la existente
    await repo.save(conversation)

    # Historial ANTES de guardar el entrante (run_agent añade el turno nuevo)
    history_msgs = await repo.get_recent_messages(
        str(conversation.id), limit=history_limit
    )
    history = [{"role": m.role, "content": m.content} for m in history_msgs]

    await repo.append_message(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=content,
            status="received",
        )
    )

    return conversation, history


def _persist_agent_reply_sync(
    conversation: Conversation, reply: str, send_status: str
) -> None:
    """Guarda la respuesta del agente con el estado real del envío.

    Best-effort: un fallo de BD no debe tumbar la tarea (la respuesta
    ya fue enviada/intentada); solo se loguea.
    """
    try:
        repo = _get_conversation_repo()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                repo.append_message(
                    Message(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=reply,
                        status=send_status,
                    )
                )
            )
        finally:
            loop.close()
    except (DomainError, ValueError) as e:
        logger.error(f"[PERSISTENCE] Could not persist agent reply: {e}")


def _resolve_whatsapp_credentials_sync(client_id: str) -> tuple[str, str, bool]:
    """Resuelve (phone_number_id, access_token, is_client_owned) para el envío.

    Estrategia de fallback (Fase 3, tarea 3.2):
    1. Si el cliente tiene credenciales propias (phone_number_id + token
       descifrado no vacíos) → se usan esas, is_client_owned=True.
    2. Si no → fallback a las credenciales GLOBALES de env
       (settings.whatsapp_phone_number_id/access_token), pensadas para
       el número de pruebas único del MVP. Se loguea claramente que se
       usó el fallback global, para poder auditar qué tenants aún no
       tienen credenciales propias configuradas.
    3. Si tampoco hay credenciales globales → ("", "", False); el
       llamador debe tratarlo como "skipped" (comportamiento actual).
    """
    settings = get_settings()

    try:
        from app.infrastructure.http.supabase_client import SupabaseHttpClient
        from app.infrastructure.persistence.client_repository import (
            SupabaseClientRepository,
        )

        db = SupabaseHttpClient(settings.supabase_url, settings.supabase_service_key)
        repo = SupabaseClientRepository(db)

        loop = asyncio.new_event_loop()
        try:
            creds = loop.run_until_complete(repo.get_whatsapp_credentials(client_id))
        finally:
            loop.close()

        if creds.has_credentials:
            return creds.phone_number_id, creds.access_token, True
    except Exception as exc:  # noqa: BLE001 — nunca debe tumbar el envío
        logger.error(f"[WHATSAPP] Error resolviendo credenciales del tenant {client_id}: {exc}")

    # Fallback: credenciales globales de env (número de pruebas del MVP).
    if settings.whatsapp_phone_number_id and settings.whatsapp_access_token:
        logger.warning(
            f"[WHATSAPP] client_id={client_id} sin credenciales propias — "
            "usando credenciales GLOBALES de env (fallback MVP). Configura "
            "credenciales propias vía /clients/{client_id}/connect-whatsapp."
        )
        return settings.whatsapp_phone_number_id, settings.whatsapp_access_token, False

    return "", "", False


def _send_whatsapp_message(client_id: str, phone: str, text: str, settings) -> str:
    """Send WhatsApp message via Meta Cloud API, con credenciales por tenant.

    Resuelve las credenciales del cliente (tarea 3.2); si el cliente no
    tiene credenciales propias, aplica el fallback a las credenciales
    globales de env (necesario mientras solo exista el número de pruebas
    único del MVP). Sin credenciales en NINGÚN nivel, el comportamiento
    es idéntico al anterior: se loguea y se retorna "skipped" (el
    mensaje no se envía, no se simula un envío exitoso).

    Returns:
        "sent" si Meta confirmó el envío, "failed" si el envío falló,
        "skipped" si no hay credenciales disponibles en ningún nivel.
    """
    phone_number_id, access_token, _is_client_owned = _resolve_whatsapp_credentials_sync(
        client_id
    )

    if not phone_number_id or not access_token:
        logger.warning(
            "[WHATSAPP] Sin credenciales (ni del tenant ni globales) — "
            "message NOT sent (status=skipped)"
        )
        logger.info(f"[WHATSAPP] To: {phone} | {text[:100]}")
        return "skipped"

    sender = WhatsAppSender(api_version=settings.whatsapp_api_version)
    result = sender.send(
        phone_number_id=phone_number_id,
        access_token=access_token,
        to=phone,
        text=text,
    )

    if not result.ok:
        logger.error(
            f"[WHATSAPP] Envío fallido a {phone} (categoria={result.status.value}): "
            f"{result.detail}"
        )

    return result.to_legacy_status()
