"""Configuración de Celery para tareas asíncronas."""

from celery import Celery

from app.infrastructure.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "agencia-ia",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=[
        "app.infrastructure.config.tasks",
        "app.infrastructure.celery.reminders",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30,
    task_soft_time_limit=25,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# ----------------------------------------------------------------------
# Celery beat: job periódico de recordatorios de cita (Fase 4, tarea 4.2)
# ----------------------------------------------------------------------
# Frecuencia elegida: cada `reminder_beat_interval_minutes` (default 10,
# dentro del rango pedido de 5-15 min). Justificación:
# - `send_appointment_reminders` selecciona citas cuyo instante de
#   recordatorio (starts_at - offset_del_cliente) cae en la ventana
#   [now, now + intervalo). Con el beat corriendo exactamente cada
#   `intervalo` minutos, cada instante de recordatorio es cubierto por
#   EXACTAMENTE una ejecución (sin huecos ni solapes), siempre que el
#   beat no se retrase más de un ciclo.
# - reminder_sent_at IS NULL es además la salvaguarda de idempotencia:
#   aunque el beat se retrase o una ejecución se solape con la
#   siguiente, una cita ya marcada no vuelve a seleccionarse ni a
#   reenviarse (ver app/infrastructure/celery/reminders.py).
# - 10 minutos es un compromiso razonable entre precisión del
#   recordatorio (no llega con horas de adelanto/atraso respecto al
#   offset configurado) y carga sobre Supabase/Meta (no crea un
#   volumen de ejecuciones excesivo como bajaría a 5 min).
celery_app.conf.beat_schedule = {
    "send-appointment-reminders": {
        "task": "send_appointment_reminders",
        "schedule": settings.reminder_beat_interval_minutes * 60.0,
    },
}
