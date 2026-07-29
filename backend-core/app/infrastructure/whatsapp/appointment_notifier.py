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
from app.infrastructure.whatsapp.channel import (
    build_whatsapp_sender,
    resolve_global_channel_credentials,
)
from app.infrastructure.whatsapp.sender import WhatsAppSendResult

logger = logging.getLogger(__name__)


class WhatsAppAppointmentNotifier(AppointmentNotificationPort):
    """Notificador de citas que envía la confirmación por WhatsApp (Meta o YCloud)."""

    def __init__(self, sender=None) -> None:
        self._sender = sender

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

        from app.infrastructure.config.settings import get_settings

        sender = self._sender or build_whatsapp_sender(get_settings())
        try:
            result: WhatsAppSendResult = await asyncio.to_thread(
                sender.send,
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

    async def send_team_alert(
        self,
        client_id: str,
        contact_phone: str,
        contact_name: str,
        business_name: str,
        starts_at_label: str,
        notes: str = "",
    ) -> bool:
        from app.infrastructure.config.settings import get_settings

        settings = get_settings()
        team_phone = (settings.team_notify_whatsapp or "").strip()
        if not team_phone:
            logger.info(
                "[APPOINTMENT_NOTIFY] TEAM_NOTIFY_WHATSAPP vacío — "
                "alerta de equipo omitida."
            )
            return False

        try:
            phone_number_id, access_token = await self._resolve_credentials(client_id)
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.error(
                f"[APPOINTMENT_NOTIFY] Error resolviendo credenciales para "
                f"alerta equipo (client_id={client_id}): {exc}"
            )
            return False

        if not phone_number_id or not access_token:
            logger.warning(
                f"[APPOINTMENT_NOTIFY] Sin credenciales — alerta equipo NO enviada "
                f"(client_id={client_id})."
            )
            return False

        name = (contact_name or "").strip() or "Sin nombre"
        notes_line = f"\nNotas: {notes.strip()}" if notes and notes.strip() else ""
        text = (
            f"📅 Nueva demo agendada — {business_name or 'Orinoco'}\n"
            f"Contacto: {name} ({contact_phone})\n"
            f"Cuándo: {starts_at_label}"
            f"{notes_line}"
        )

        sender = self._sender or build_whatsapp_sender(settings)
        try:
            result: WhatsAppSendResult = await asyncio.to_thread(
                sender.send,
                phone_number_id,
                access_token,
                team_phone,
                text,
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.error(
                f"[APPOINTMENT_NOTIFY] Excepción enviando alerta equipo "
                f"(client_id={client_id}): {exc}"
            )
            return False

        if not result.ok:
            logger.error(
                f"[APPOINTMENT_NOTIFY] Alerta equipo no enviada "
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

        global_id, global_token = resolve_global_channel_credentials(settings)
        if global_id and global_token:
            logger.warning(
                f"[APPOINTMENT_NOTIFY] client_id={client_id} sin credenciales "
                "propias — usando credenciales GLOBALES de env (fallback MVP)."
            )
            return global_id, global_token

        return "", ""
