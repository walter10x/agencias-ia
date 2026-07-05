"""Puerto de notificación de citas (DRIVEN PORT).

Desacopla la capa de aplicación/tools del canal de mensajería concreto
(WhatsApp Cloud API). La tool `agendar_cita` (infrastructure/ai/tools.py)
consume este puerto para confirmar la cita al contacto sin conocer
Meta/httpx directamente — el adaptador concreto vive en
`app.infrastructure.whatsapp.appointment_notifier`.

Contrato best-effort: los adaptadores NO deben propagar excepciones de
red/API al llamador; deben capturarlas, loguearlas, y retornar False.
La cita ya fue creada en el dominio antes de notificar — un fallo de
notificación nunca debe deshacer ni bloquear la creación de la cita.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AppointmentNotificationPort(ABC):
    """Envía una confirmación de cita al contacto final."""

    @abstractmethod
    async def send_confirmation(
        self,
        client_id: str,
        contact_phone: str,
        business_name: str,
        starts_at_label: str,
    ) -> bool:
        """Envía la confirmación de la cita agendada.

        Args:
            client_id: ID del tenant (negocio) dueño de la cita — se usa
                para resolver las credenciales de WhatsApp del tenant.
            contact_phone: Teléfono del contacto que agendó la cita.
            business_name: Nombre del negocio, para incluir en el mensaje.
            starts_at_label: Fecha/hora de la cita ya formateada en texto
                legible (ej. "miércoles 10 de julio a las 15:00").

        Returns:
            True si el envío fue exitoso, False en cualquier otro caso
            (sin credenciales, error de Meta, excepción de red, etc).
            NUNCA lanza excepción — best-effort por diseño.
        """
        ...
