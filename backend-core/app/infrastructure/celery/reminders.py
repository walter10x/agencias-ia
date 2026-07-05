"""Tarea periódica de recordatorios de cita por WhatsApp (Fase 4).

`send_appointment_reminders` es disparada por Celery beat (ver
app.infrastructure.config.celery_app::beat_schedule) cada
`settings.reminder_beat_interval_minutes` minutos.

Estrategia de selección de citas (documentada también en el puerto
`AppointmentRepository.find_reminder_candidates`):

El offset de recordatorio (`reminder_offset_minutes`) es una config
POR CLIENTE que vive en el JSONB `business_hours` de la tabla `clients`
(Fase 4, ver `BusinessSchedule.reminder_offset_minutes` y
`SupabaseClientRepository._row_to_schedule`). Esto significa que el
instante exacto en el que una cita "debe" recordarse
(`starts_at - offset`) depende del cliente dueño de la cita, y no se
puede expresar como una única condición SQL sobre la tabla
`appointments` sin un join dinámico por tenant (PostgREST no soporta
subqueries correlacionadas desde este cliente HTTP minimalista).

La solución adoptada, más simple que un join y suficiente para el
volumen esperado del MVP:
1. Query cross-tenant amplia: traer todas las citas activas
   (pending/confirmed) con reminder_sent_at IS NULL y starts_at dentro
   de una ventana amplia (`REMINDER_CANDIDATES_WINDOW_HOURS`, ~48h)
   hacia adelante. Ver `find_reminder_candidates`.
2. Filtrar en Python: para cada cita, resolver el BusinessSchedule (y
   por tanto el offset) de SU cliente, calcular
   `remind_at = starts_at - offset`, y comparar contra la ventana de
   esta ejecución del beat: [now, now + intervalo_beat). Solo se
   procesan las citas cuyo remind_at cae en esa ventana.

Cobertura sin huecos ni duplicados: como el beat corre cada
`intervalo_beat` minutos y la ventana de cada ejecución es
[now, now + intervalo_beat), cada instante remind_at es cubierto por
exactamente una ejecución (asumiendo el beat puntual). La salvaguarda
real de "nunca duplicado" es `reminder_sent_at IS NULL`: aunque el beat
se retrase, se solape, o el worker se caiga a mitad de una ejecución,
una cita ya marcada nunca vuelve a seleccionarse.

Plantilla HSM de Meta (pendiente, fuera de este código): fuera de la
ventana de 24h de una conversación (que es exactamente el caso de un
recordatorio de 24h de antelación), Meta exige el envío de un mensaje
de plantilla (HSM) pre-aprobado por Meta Business Manager — un mensaje
de texto libre como el que construye `build_reminder_message` será
RECHAZADO por la API en producción si la ventana de 24h ya se cerró.
El registro/aprobación de esa plantilla es un proceso externo y manual
en Meta Business Manager (tarea 4.1 del plan, con lead time de
días/semanas) que este código NO puede automatizar. `WhatsAppSender.send`
solo sabe enviar mensajes de texto libre; el punto exacto donde se debe
sustituir por el envío de la plantilla aprobada está marcado más abajo
en `_send_reminder`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from app.domain.appointment.entity import Appointment, BusinessSchedule
from app.infrastructure.config.celery_app import celery_app
from app.infrastructure.config.settings import get_settings
from app.infrastructure.whatsapp.sender import WhatsAppSender

logger = get_task_logger(__name__)

# Ventana amplia de la query cross-tenant (paso 1 de la estrategia, ver
# docstring del módulo). 48h cubre holgadamente cualquier
# reminder_offset_minutes razonable (el default es 24h) sin traer un
# volumen de filas excesivo por ejecución.
REMINDER_CANDIDATES_WINDOW_HOURS = 48

_WEEKDAY_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MONTH_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _format_starts_at_label(starts_at: datetime) -> str:
    """Formatea un datetime (UTC) como texto legible en español.

    Mismo formato que `_format_starts_at_label` de
    `app.infrastructure.ai.tools` (confirmación de cita, Fase 2.6) —
    duplicado deliberadamente aquí en vez de importado, para no acoplar
    la tarea periódica de infraestructura Celery al paquete de IA
    (tools.py importa dependencias de LLM que no hacen falta para
    enviar un recordatorio).
    """
    weekday = _WEEKDAY_ES[starts_at.weekday()]
    month = _MONTH_ES[starts_at.month]
    return f"{weekday} {starts_at.day} de {month} a las {starts_at.strftime('%H:%M')}"


def build_reminder_message(business_name: str, starts_at_label: str) -> str:
    """Construye el texto del recordatorio de cita — punto CENTRAL del mensaje.

    IMPORTANTE — plantilla HSM de Meta (tarea 4.1, pendiente/externa):
    Este mensaje es texto libre. Meta Cloud API solo permite texto libre
    dentro de la ventana de 24h de la última interacción del contacto;
    un recordatorio enviado con el offset por defecto (24h antes de la
    cita) casi siempre cae FUERA de esa ventana, por lo que en
    producción real Meta rechazará este envío con el error 131047
    (re-engagement/fuera de ventana 24h — ver
    `app.infrastructure.whatsapp.sender._META_ERROR_CODE_MAP`).
    La solución correcta es enviar un mensaje de PLANTILLA (HSM)
    pre-aprobado por Meta Business Manager en vez de este texto libre.
    Ese registro/aprobación es un proceso manual fuera del alcance de
    este código (ver PLAN-MVP.md, Fase 4, tarea 4.1). Cuando la
    plantilla esté aprobada, este es el punto a reemplazar: en vez de
    `WhatsAppSender.send(...)` con este texto, se debería invocar el
    envío de plantilla (nuevo método en WhatsAppSender o adaptador
    dedicado) con los parámetros de la plantilla aprobada.
    """
    negocio = business_name or "nuestro negocio"
    return (
        f"¡Hola! Te recordamos tu cita en {negocio} para el {starts_at_label}. "
        "Si necesitas cambiarla o cancelarla, escríbenos por este mismo chat."
    )


@celery_app.task(name="send_appointment_reminders")
def send_appointment_reminders() -> dict:
    """Tarea periódica: busca citas próximas y envía el recordatorio pendiente.

    Resiliente por diseño (tarea 5 del plan): un cliente sin
    credenciales, un fallo de resolución de horario, o un fallo de
    envío para UNA cita no interrumpen el procesamiento de las demás.
    Cada cita se marca individualmente tras un envío exitoso, así un
    fallo parcial nunca reenvía las que ya tuvieron éxito.

    Returns:
        dict con conteo de candidatas evaluadas, recordatorios enviados
        y saltados (por fuera de ventana, sin credenciales, o error).
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_send_appointment_reminders_async())
    finally:
        loop.close()


async def _send_appointment_reminders_async(now: datetime | None = None) -> dict:
    """Lógica async de la tarea. `now` es inyectable solo para tests
    (evita mockear `datetime.now` globalmente); en producción siempre se
    usa el reloj real."""
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=settings.reminder_beat_interval_minutes)

    appointment_repo = _build_appointment_repo()
    schedule_repo = _build_schedule_repo()
    client_repo = _build_client_repo()
    sender = WhatsAppSender(api_version=settings.whatsapp_api_version)

    candidates = await appointment_repo.find_reminder_candidates(
        starts_from=now,
        starts_to=now + timedelta(hours=REMINDER_CANDIDATES_WINDOW_HOURS),
    )

    evaluated = len(candidates)
    sent = 0
    skipped_out_of_window = 0
    skipped_no_credentials = 0
    failed = 0

    # Cache de BusinessSchedule por cliente dentro de esta ejecución: varias
    # citas del mismo cliente no deberían disparar N lecturas idénticas.
    schedule_cache: dict[str, BusinessSchedule | None] = {}

    for appointment in candidates:
        client_id = str(appointment.client_id)

        try:
            schedule = schedule_cache.get(client_id)
            if client_id not in schedule_cache:
                schedule = await schedule_repo.get_business_schedule(client_id)
                schedule_cache[client_id] = schedule
        except Exception as exc:  # noqa: BLE001 — un cliente no debe tumbar el resto
            logger.warning(
                f"[REMINDERS] No se pudo resolver el horario/offset de "
                f"client_id={client_id} (appointment_id={appointment.id}): {exc}. "
                "Se salta esta cita en este ciclo, se reintentará en el próximo."
            )
            skipped_out_of_window += 1
            continue

        if schedule is None:
            logger.warning(
                f"[REMINDERS] client_id={client_id} no encontrado — se salta "
                f"appointment_id={appointment.id}."
            )
            skipped_out_of_window += 1
            continue

        remind_at = appointment.starts_at - timedelta(
            minutes=schedule.reminder_offset_minutes
        )
        if not (now <= remind_at < window_end):
            # Fuera de la ventana de ESTA ejecución del beat — no es un
            # error, simplemente le toca a otro ciclo (o ya pasó y no
            # aplica, lo cual no debería ocurrir si el beat es puntual).
            skipped_out_of_window += 1
            continue

        try:
            client = await client_repo.find_by_id(_client_id_from_str(client_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[REMINDERS] Error cargando cliente client_id={client_id} "
                f"(appointment_id={appointment.id}): {exc}. Se salta."
            )
            skipped_no_credentials += 1
            continue

        business_name = client.name if client else ""

        try:
            phone_number_id, access_token = await _resolve_credentials(client_id)
        except Exception as exc:  # noqa: BLE001 — nunca debe tumbar el ciclo
            logger.warning(
                f"[REMINDERS] Error resolviendo credenciales de WhatsApp para "
                f"client_id={client_id} (appointment_id={appointment.id}): {exc}. "
                "Se salta esta cita, se reintentará en el próximo ciclo."
            )
            skipped_no_credentials += 1
            continue

        if not phone_number_id or not access_token:
            logger.warning(
                f"[REMINDERS] client_id={client_id} sin credenciales de "
                f"WhatsApp configuradas — recordatorio NO enviado para "
                f"appointment_id={appointment.id}. Se reintentará en el "
                "próximo ciclo (reminder_sent_at sigue NULL)."
            )
            skipped_no_credentials += 1
            continue

        ok = _send_reminder(
            sender=sender,
            phone_number_id=phone_number_id,
            access_token=access_token,
            appointment=appointment,
            business_name=business_name,
        )

        if not ok:
            # No se marca reminder_sent_at: se reintenta en el próximo
            # ciclo de beat (tarea 5 del plan — resiliencia individual).
            failed += 1
            continue

        try:
            await appointment_repo.mark_reminder_sent(str(appointment.id))
            sent += 1
        except Exception as exc:  # noqa: BLE001
            # El mensaje SÍ se envió pero no se pudo marcar: se registra
            # el riesgo de reenvío en el próximo ciclo (mejor que perder
            # el recordatorio) y se cuenta igualmente como enviado.
            logger.error(
                f"[REMINDERS] Recordatorio enviado pero no se pudo marcar "
                f"reminder_sent_at (appointment_id={appointment.id}): {exc}. "
                "Riesgo de reenvío en el próximo ciclo."
            )
            sent += 1

    result = {
        "evaluated": evaluated,
        "sent": sent,
        "skipped_out_of_window": skipped_out_of_window,
        "skipped_no_credentials": skipped_no_credentials,
        "failed": failed,
    }
    logger.info(f"[REMINDERS] Ciclo completado: {result}")
    return result


def _send_reminder(
    *,
    sender: WhatsAppSender,
    phone_number_id: str,
    access_token: str,
    appointment: Appointment,
    business_name: str,
) -> bool:
    """Envía el recordatorio de UNA cita. No lanza — retorna éxito/fallo.

    Punto de sustitución futuro por plantilla HSM: ver docstring de
    `build_reminder_message`.
    """
    label = _format_starts_at_label(appointment.starts_at)
    text = build_reminder_message(business_name, label)

    try:
        result = sender.send(
            phone_number_id=phone_number_id,
            access_token=access_token,
            to=appointment.contact_phone,
            text=text,
        )
    except Exception as exc:  # noqa: BLE001 — nunca debe tumbar el ciclo
        logger.error(
            f"[REMINDERS] Excepción enviando recordatorio "
            f"(appointment_id={appointment.id}): {exc}"
        )
        return False

    if not result.ok:
        logger.error(
            f"[REMINDERS] Envío fallido (appointment_id={appointment.id}, "
            f"categoria={result.status.value}): {result.detail}"
        )
    return result.ok


# ---------------------------------------------------------------------------
# Resolución de credenciales — mismo patrón que
# app.infrastructure.config.tasks::_resolve_whatsapp_credentials_sync
# (Fase 3, tarea 3.2), adaptado a la versión async nativa de esta tarea.
# ---------------------------------------------------------------------------


async def _resolve_credentials(client_id: str) -> tuple[str, str]:
    """Resuelve (phone_number_id, access_token) del tenant, con fallback a env.

    Reutiliza la misma estrategia de `tasks.py::_resolve_whatsapp_credentials_sync`
    y `WhatsAppAppointmentNotifier._resolve_credentials`: credenciales
    propias del cliente primero, fallback a las credenciales globales de
    env si el cliente no tiene las suyas, y ("", "") si no hay ninguna.
    """
    settings = get_settings()
    repo = _build_client_repo()

    creds = await repo.get_whatsapp_credentials(client_id)
    if creds.has_credentials:
        return creds.phone_number_id, creds.access_token

    if settings.whatsapp_phone_number_id and settings.whatsapp_access_token:
        logger.warning(
            f"[REMINDERS] client_id={client_id} sin credenciales propias — "
            "usando credenciales GLOBALES de env (fallback MVP)."
        )
        return settings.whatsapp_phone_number_id, settings.whatsapp_access_token

    return "", ""


# ---------------------------------------------------------------------------
# Construcción de adaptadores (mismo patrón que tasks.py / appointment_notifier)
# ---------------------------------------------------------------------------


def _build_supabase_client():
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


def _build_client_repo():
    from app.infrastructure.persistence.client_repository import (
        SupabaseClientRepository,
    )

    return SupabaseClientRepository(_build_supabase_client())


def _client_id_from_str(client_id: str):
    from app.domain.shared.value_objects import ClientId

    return ClientId.from_string(client_id)
