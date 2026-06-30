"""Caso de uso: enviar un email de marketing usando Resend."""

from __future__ import annotations

import httpx

from app.application.dtos import SendEmailInput, SendEmailOutput
from app.domain.email.entity import EmailLog, EmailStatus
from app.domain.email.repository import EmailRepository
from app.domain.email.templates import get_email_template
from app.domain.shared.errors import EmailError
from app.infrastructure.config.settings import get_settings


class SendEmailUseCase:
    """Envia un email via Resend API y persiste el log."""

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self, repo: EmailRepository) -> None:
        self._repo = repo
        self._settings = get_settings()

    async def execute(self, input: SendEmailInput) -> SendEmailOutput:
        template = get_email_template(input.rubro_slug, input.sequence_number)

        subject = template.subject.replace("{{business_name}}", input.business_name)
        subject = subject.replace("{{contact_name}}", input.contact_name)
        body = template.body_html.replace("{{business_name}}", input.business_name)
        body = body.replace("{{contact_name}}", input.contact_name)

        log = EmailLog(
            client_id=input.client_id,
            lead_id=input.lead_id,
            to_email=input.to_email,
            subject=subject,
            body_html=body,
            template_slug=input.rubro_slug,
            sequence_number=input.sequence_number,
            status=EmailStatus.SENT,
        )

        resend_id = ""
        error_msg = ""

        api_key = getattr(self._settings, "resend_api_key", "")
        email_from = getattr(self._settings, "email_from", "Agencia IA <noreply@agencia-ia.com>")

        if api_key:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        self.RESEND_API_URL,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "from": email_from,
                            "to": [input.to_email],
                            "subject": subject,
                            "html": body,
                        },
                    )
                    if response.is_success:
                        data = response.json()
                        resend_id = data.get("id", "")
                        log.resend_id = resend_id
                    else:
                        error_msg = response.text
                        log.status = EmailStatus.BOUNCED
                        log.error_message = error_msg
            except httpx.RequestError as exc:
                error_msg = str(exc)
                log.status = EmailStatus.BOUNCED
                log.error_message = error_msg
        else:
            # Dev mode: no API key configured, mark as sent but note it
            log.error_message = "RESEND_API_KEY not configured — email logged but not sent"

        await self._repo.save(log)

        if error_msg and api_key:
            raise EmailError(f"Failed to send email: {error_msg}")

        return SendEmailOutput(
            id=str(log.id),
            status=log.status.value if isinstance(log.status, EmailStatus) else str(log.status),
        )
