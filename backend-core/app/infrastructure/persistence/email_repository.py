"""Supabase adapter for EmailRepository port (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.domain.email.entity import EmailLog, EmailStatus
from app.domain.email.repository import EmailRepository
from app.domain.shared.errors import DomainError
from app.infrastructure.http.supabase_client import SupabaseHttpClient


class SupabaseEmailRepository(EmailRepository):
    """Supabase implementation of EmailRepository."""

    TABLE = "email_logs"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    async def save(self, log: EmailLog) -> None:
        row = {
            "id": str(log.id),
            "client_id": str(log.client_id),
            "lead_id": str(log.lead_id) if log.lead_id else None,
            "to_email": log.to_email,
            "subject": log.subject,
            "body_html": log.body_html,
            "template_slug": log.template_slug,
            "sequence_number": log.sequence_number,
            "status": log.status.value if isinstance(log.status, EmailStatus) else log.status,
            "resend_id": log.resend_id,
            "error_message": log.error_message,
            "sent_at": log.sent_at.isoformat(),
            "created_at": log.created_at.isoformat(),
        }
        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .insert(row)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)

    async def find_by_id(self, log_id: str) -> Optional[EmailLog]:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("id", log_id)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_email_log(result.data[0])

    async def list_by_client(
        self,
        client_id: str,
        lead_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[EmailLog]:
        try:
            query = (
                self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .order("sent_at", desc=True)
                .limit(limit)
                .offset(offset)
            )
            if lead_id:
                query = query.eq("lead_id", lead_id)

            result = await asyncio.to_thread(lambda: query.execute())
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_email_log(row) for row in result.data]

    async def count_by_client(self, client_id: str) -> int:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("id")
                .eq("client_id", client_id)
                .execute()
            )
            return len(result.data)
        except Exception as exc:
            self._raise_domain_error(exc)
            return 0

    async def get_stats(self, client_id: str) -> dict:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("id,status,template_slug")
                .eq("client_id", client_id)
                .execute()
            )
            rows = result.data
            total = len(rows)

            total_opened = 0
            total_clicked = 0
            total_bounced = 0
            by_template: dict[str, int] = {}

            for row in rows:
                s = row.get("status", "sent")
                if s == "opened":
                    total_opened += 1
                elif s == "clicked":
                    total_clicked += 1
                elif s == "bounced":
                    total_bounced += 1

                slug = row.get("template_slug", "")
                if slug:
                    by_template[slug] = by_template.get(slug, 0) + 1

            open_rate = (total_opened / total * 100) if total > 0 else 0.0
            click_rate = (total_clicked / total * 100) if total > 0 else 0.0

            return {
                "total_sent": total,
                "total_opened": total_opened,
                "total_clicked": total_clicked,
                "total_bounced": total_bounced,
                "open_rate": round(open_rate, 2),
                "click_rate": round(click_rate, 2),
                "by_template": by_template,
            }
        except Exception as exc:
            self._raise_domain_error(exc)
            return {
                "total_sent": 0,
                "total_opened": 0,
                "total_clicked": 0,
                "total_bounced": 0,
                "open_rate": 0.0,
                "click_rate": 0.0,
                "by_template": {},
            }

    @staticmethod
    def _row_to_email_log(row: dict) -> EmailLog:
        log = EmailLog(
            id=UUID(row["id"]),
            client_id=UUID(row["client_id"]),
            lead_id=UUID(row["lead_id"]) if row.get("lead_id") else None,
            to_email=row["to_email"],
            subject=row["subject"],
            body_html=row.get("body_html", ""),
            template_slug=row.get("template_slug", ""),
            sequence_number=row.get("sequence_number", 1),
            status=EmailStatus(row["status"]),
            error_message=row.get("error_message", ""),
        )
        log.resend_id = row.get("resend_id", "")
        log.sent_at = datetime.fromisoformat(row["sent_at"]) if row.get("sent_at") else datetime.now(timezone.utc)
        log.created_at = datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc)
        return log

    @staticmethod
    def _raise_domain_error(exc: Exception) -> None:
        import json

        import httpx

        message = str(exc)
        try:
            if "Supabase error:" in message:
                body_str = message.split("Supabase error:", 1)[1].strip()
                body = json.loads(body_str)
                message = body.get("message", message)
        except (json.JSONDecodeError, IndexError):
            pass

        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            raise DomainError("Database connection failed") from exc
        if "connection" in message.lower() or "timeout" in message.lower():
            raise DomainError("Database connection failed") from exc

        raise DomainError(f"Database error: {message}") from exc
