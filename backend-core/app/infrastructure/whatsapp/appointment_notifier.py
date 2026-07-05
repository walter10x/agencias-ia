"""Adaptador de AppointmentNotificationPort vía WhatsApp Cloud API.

Implementa la confirmación de cita (Fase 2, tarea 2.6) reutilizando
`WhatsAppSender` y la misma estrategia de resolución de credenciales por
tenant (con fallback a env) que usa `tasks.py::_send_whatsapp_message`.

Best-effort por contrato del puerto: cualquier error (sin credenciales,
fallo de Meta, excepción de red) se captura y loguea aquí; la tool que
llama a este adaptador (agendar_cita) nunca debe fallar por esto.
"""

from __future__ import annotations

import asyncio
import logging

from app.application.ports.appointment_notification_port import (
    AppointmentNotificationPort,
)
from app.infrastructure.whatsapp.sender import WhatsAppSender

logger = logging.getLogger(__name__)


class WhatsAppAppointmentNotifier(AppointmentNotificationPort):
    """Notificador de citas que envía la confirmación por WhatsApp Cloud API."""

    def __init__(self, sender: WhatsAppSender | None = None) -> None:
        self._sender = sender or WhatsAppSender()

    async def send_confirmation(
        self,
        client_id: str,
        contact_phone: str,
        business_name: str,
        starts_at_label: str,
    ) -> bool:
        try:
            phone_number_id, access_token = await self._resolve_credentials(client_id)
        except Exception as exc:  # noqa: BLE001 — best-effort, nunca propagar
            logger.error(
                f"[APPOINTMENT_NOTIFY] Error resolviendo credenciales "
                f"(client_id={client_id}): {exc}"
            )
            return False

        if not phone_number_id or not access_token:
            logger.warning(
                f"[APPOINTMENT_NOTIFY] Sin credenciales de WhatsApp para "
                f"client_id={client_id} — confirmación NO enviada "
                f"(la cita se creó igualmente)."
            )
            return False

        text = (
            f"¡Hola! Tu cita en {business_name or 'nuestro negocio'} quedó "
            f"confirmada para el {starts_at_label}. Si necesitas cambiarla, "
            "escríbenos por este mismo chat."
        )

        try:
            result = await asyncio.to_thread(
                self._sender.send,
                phone_number_id,
                access_token,
                contact_phone,
                text,
            )
        except Exception as exc:  # noqa: BLE001 — best-effort, nunca propagar
            logger.error(
                f"[APPOINTMENT_NOTIFY] Excepción enviando confirmación "
                f"(client_id={client_id}): {exc}"
            )
            return False

        if not result.ok:
            logger.error(
                f"[APPOINTMENT_NOTIFY] Confirmación no enviada "
                f"(client_id={client_id}, categoria={result.status.value}): "
                f"{result.detail}"
            )
        return result.ok

    async def _resolve_credentials(self, client_id: str) -> tuple[str, str]:
        """Resuelve credenciales del tenant, con fallback a env (igual que tasks.py)."""
        from app.infrastructure.config.settings import get_settings
        from app.infrastructure.http.supabase_client import SupabaseHttpClient
        from app.infrastructure.persistence.client_repository import (
            SupabaseClientRepository,
        )

        settings = get_settings()
        db = SupabaseHttpClient(settings.supabase_url, settings.supabase_service_key)
        repo = SupabaseClientRepository(db)

        creds = await repo.get_whatsapp_credentials(client_id)
        if creds.has_credentials:
            return creds.phone_number_id, creds.access_token

        if settings.whatsapp_phone_number_id and settings.whatsapp_access_token:
            logger.warning(
                f"[APPOINTMENT_NOTIFY] client_id={client_id} sin credenciales "
                "propias — usando credenciales GLOBALES de env (fallback MVP)."
            )
            return settings.whatsapp_phone_number_id, settings.whatsapp_access_token

        return "", ""
