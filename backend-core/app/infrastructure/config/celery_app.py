"""Configuración de Celery para tareas asíncronas."""

from celery import Celery

from app.infrastructure.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "agencia-ia",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=["app.infrastructure.config.tasks"],
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
