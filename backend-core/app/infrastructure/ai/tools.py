"""Tools nativas del agente IA (function calling).

Las tools de agenda (consultar_disponibilidad, agendar_cita, cancelar_cita)
se ejecutan LOCALMENTE invocando los use cases del módulo de agenda con el
client_id del contexto del tenant — ya no se delega a n8n.

Cualquier otra tool definida en la configuración del agente devuelve el
mensaje de "no configurada" (comportamiento compatible con el anterior).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.agent.entity import AgentTool
from app.domain.shared.errors import DomainError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Definición de las tools nativas de agenda
# ---------------------------------------------------------------------------

CONSULTAR_DISPONIBILIDAD = "consultar_disponibilidad"
AGENDAR_CITA = "agendar_cita"
CANCELAR_CITA = "cancelar_cita"

AGENDA_TOOLS = frozenset({CONSULTAR_DISPONIBILIDAD, AGENDAR_CITA, CANCELAR_CITA})

# Schemas de parámetros (OpenAI function calling) por tool nativa
_AGENDA_TOOL_PARAMETERS: dict[str, dict[str, Any]] = {
    CONSULTAR_DISPONIBILIDAD: {
        "type": "object",
        "properties": {
            "fecha": {
                "type": "string",
                "description": "Día a consultar en formato YYYY-MM-DD, ej. 2026-07-10",
            },
        },
        "required": ["fecha"],
    },
    AGENDAR_CITA: {
        "type": "object",
        "properties": {
            "fecha_hora": {
                "type": "string",
                "description": (
                    "Fecha y hora de inicio de la cita en formato ISO 8601 "
                    "(YYYY-MM-DDTHH:MM), en hora local del negocio. Ej. 2026-07-10T15:00"
                ),
            },
            "nombre": {
                "type": "string",
                "description": "Nombre de la persona que agenda la cita",
            },
            "telefono": {
                "type": "string",
                "description": "Teléfono de contacto (WhatsApp) de la persona",
            },
            "notas": {
                "type": "string",
                "description": "Notas opcionales (motivo de la cita, servicio, etc.)",
            },
        },
        "required": ["fecha_hora", "nombre"],
    },
    CANCELAR_CITA: {
        "type": "object",
        "properties": {
            "referencia": {
                "type": "string",
                "description": (
                    "Referencia de la cita a cancelar: el ID de la cita "
                    "(si se conoce) o el teléfono del contacto para cancelar "
                    "su próxima cita"
                ),
            },
        },
        "required": ["referencia"],
    },
}

def agent_tools_to_openai_format(tools: list[AgentTool]) -> list[dict[str, Any]]:
    """Convierte AgentTool a formato OpenAI function calling.

    Las tools de agenda llevan schemas de parámetros tipados reales;
    el resto conserva el schema genérico de un solo campo "input".

    Args:
        tools: Lista de tools definidas en la configuración del agente.

    Returns:
        Lista de tool definitions en formato OpenAI.
    """
    definitions: list[dict[str, Any]] = []
    for tool in tools:
        if tool.name in _AGENDA_TOOL_PARAMETERS:
            parameters = _AGENDA_TOOL_PARAMETERS[tool.name]
        else:
            parameters = {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": f"Input para la herramienta {tool.name}",
                    }
                },
                "required": ["input"],
            }
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                },
            }
        )
    return definitions


# ---------------------------------------------------------------------------
# Factories de dependencias (patcheables en tests)
# ---------------------------------------------------------------------------


def _build_supabase_client():
    from app.infrastructure.config.settings import get_settings
    from app.infrastructure.http.supabase_client import SupabaseHttpClient

    settings = get_settings()
    return SupabaseHttpClient(settings.supabase_url, settings.supabase_service_key)


def _build_appointment_repo():
    from app.infrastructure.persistence.appointment_repository import (
        SupabaseAppointmentRepository,
    )

    return SupabaseAppointmentRepository(_build_supabase_client())


def _build_schedule_repo():
    from app.infrastructure.persistence.client_repository import (
        SupabaseClientRepository,
    )

    return SupabaseClientRepository(_build_supabase_client())


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _parse_arguments(tool_input: Any) -> dict[str, Any]:
    """Normaliza los argumentos del tool call a un dict."""
    if isinstance(tool_input, dict):
        return tool_input
    if isinstance(tool_input, str):
        try:
            parsed = json.loads(tool_input)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {"input": tool_input}
    return {"input": str(tool_input)}


async def execute_tool(
    tool_name: str,
    tool_input: Any,
    client_context: dict[str, Any] | None = None,
) -> str:
    """Ejecuta una herramienta del agente localmente.

    Args:
        tool_name: Nombre de la herramienta a ejecutar.
        tool_input: Argumentos del tool call (dict o JSON string).
        client_context: Contexto del tenant; debe incluir "id" (client_id).

    Returns:
        Resultado de la ejecución como string (se inyecta como mensaje
        role=tool para que el LLM lo procese).
    """
    if tool_name not in AGENDA_TOOLS:
        return f"Tool '{tool_name}' no está configurada."

    context = client_context or {}
    client_id = str(context.get("id") or "").strip()
    if not client_id:
        logger.error("execute_tool(%s) sin client_id en client_context", tool_name)
        return "Error interno: no se pudo identificar el negocio para esta operación."

    arguments = _parse_arguments(tool_input)

    try:
        if tool_name == CONSULTAR_DISPONIBILIDAD:
            return await _consultar_disponibilidad(client_id, arguments)
        if tool_name == AGENDAR_CITA:
            return await _agendar_cita(client_id, arguments, context)
        return await _cancelar_cita(client_id, arguments, context)
    except DomainError as e:
        return f"No se pudo completar la operación: {e.message}"
    except Exception as e:  # noqa: BLE001 — el LLM necesita un string siempre
        logger.exception("Error ejecutando tool '%s'", tool_name)
        return f"Error ejecutando tool '{tool_name}': {e}"


# ---------------------------------------------------------------------------
# Implementación de cada tool
# ---------------------------------------------------------------------------


async def _consultar_disponibilidad(client_id: str, arguments: dict[str, Any]) -> str:
    from app.application.appointment.get_availability import GetAvailabilityUseCase
    from app.application.dtos import GetAvailabilityInput

    fecha = str(arguments.get("fecha") or arguments.get("input") or "").strip()
    if not fecha:
        return "Falta el parámetro 'fecha' (formato YYYY-MM-DD)."

    uc = GetAvailabilityUseCase(
        repo=_build_appointment_repo(),
        schedule_repo=_build_schedule_repo(),
    )
    output = await uc.execute(GetAvailabilityInput(client_id=client_id, date=fecha))

    if not output.slots:
        return (
            f"No hay horarios disponibles para el {output.date}. "
            "Sugiere al cliente otro día."
        )

    labels = ", ".join(slot.label for slot in output.slots)
    return (
        f"Horarios disponibles para el {output.date} "
        f"(duración {output.slot_duration_minutes} min): {labels}"
    )


async def _agendar_cita(
    client_id: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from app.application.appointment.create_appointment import CreateAppointmentUseCase
    from app.application.dtos import CreateAppointmentInput

    fecha_hora = str(arguments.get("fecha_hora") or arguments.get("input") or "").strip()
    nombre = str(arguments.get("nombre") or context.get("contact_name") or "").strip()
    telefono = str(
        arguments.get("telefono")
        or context.get("contact_phone")
        or context.get("phone")
        or ""
    ).strip()
    notas = str(arguments.get("notas") or "").strip()

    if not fecha_hora:
        return "Falta el parámetro 'fecha_hora' (formato YYYY-MM-DDTHH:MM)."
    if not telefono:
        return (
            "Falta el teléfono de contacto. Pide al cliente su número "
            "de teléfono para confirmar la cita."
        )

    uc = CreateAppointmentUseCase(
        repo=_build_appointment_repo(),
        schedule_repo=_build_schedule_repo(),
    )
    output = await uc.execute(
        CreateAppointmentInput(
            client_id=client_id,
            starts_at=fecha_hora,
            contact_phone=telefono,
            contact_name=nombre,
            notes=notas,
            conversation_id=context.get("conversation_id"),
        )
    )
    return (
        f"Cita agendada correctamente para {nombre or 'el cliente'} "
        f"el {output.starts_at} (referencia: {output.id}). "
        "Confirma al cliente la fecha y hora."
    )


async def _cancelar_cita(
    client_id: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from app.application.appointment.cancel_appointment import CancelAppointmentUseCase
    from app.application.dtos import CancelAppointmentInput
    from app.domain.shared.errors import AppointmentNotFoundError

    referencia = str(
        arguments.get("referencia")
        or arguments.get("input")
        or context.get("contact_phone")
        or context.get("phone")
        or ""
    ).strip()
    if not referencia:
        return "Falta el parámetro 'referencia' (ID de la cita o teléfono del contacto)."

    repo = _build_appointment_repo()
    appointment_id: str | None = None

    try:
        UUID(referencia)
        appointment_id = referencia
    except ValueError:
        # No es un UUID: tratar la referencia como teléfono del contacto
        appointment = await repo.find_next_by_phone(
            client_id=client_id,
            contact_phone=referencia,
            now=datetime.now(timezone.utc),
        )
        if appointment is None:
            return (
                f"No se encontró ninguna cita próxima para '{referencia}'. "
                "Verifica el teléfono o el ID de la cita."
            )
        appointment_id = str(appointment.id)

    uc = CancelAppointmentUseCase(repo=repo)
    try:
        output = await uc.execute(
            CancelAppointmentInput(client_id=client_id, appointment_id=appointment_id)
        )
    except AppointmentNotFoundError:
        return (
            f"No se encontró la cita '{referencia}' para este negocio. "
            "Verifica la referencia."
        )
    return (
        f"Cita del {output.starts_at} cancelada correctamente "
        f"(referencia: {output.id}). Informa al cliente."
    )
