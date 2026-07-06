"""Tareas Celery de infraestructura organizadas por dominio funcional.

`app.infrastructure.config.tasks` contiene el orquestador principal del
pipeline de mensajes (Fase 1/3). Este paquete agrupa tareas periódicas
(Celery beat) que no forman parte de ese pipeline síncrono de webhook,
empezando por los recordatorios de cita (Fase 4).
"""
