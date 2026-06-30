"""Supabase adapter for LeadRepository port (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.domain.lead.entity import Lead, LeadStatus
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import DomainError
from app.infrastructure.http.supabase_client import SupabaseHttpClient


class SupabaseLeadRepository(LeadRepository):
    """Supabase implementation of LeadRepository."""

    TABLE = "leads"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    async def save(self, lead: Lead) -> None:
        row = {
            "id": str(lead.id),
            "client_id": str(lead.client_id),
            "phone": lead.phone,
            "name": lead.name,
            "status": lead.status.value if isinstance(lead.status, LeadStatus) else lead.status,
            "source": lead.source,
            "score": lead.score,
            "notes": lead.notes,
            "last_contacted_at": (
                lead.last_contacted_at.isoformat() if lead.last_contacted_at else None
            ),
            "created_at": lead.created_at.isoformat(),
            "updated_at": lead.updated_at.isoformat(),
        }
        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .upsert(row, on_conflict="id")
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)

    async def find_by_id(self, lead_id: str) -> Optional[Lead]:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("id", lead_id)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_lead(result.data[0])

    async def find_by_client_and_phone(
        self, client_id: str, phone: str
    ) -> Optional[Lead]:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .eq("phone", phone)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_lead(result.data[0])

    async def list_by_client(
        self,
        client_id: str,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Lead]:
        try:
            query = (
                self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .order("updated_at", desc=True)
                .limit(limit)
                .offset(offset)
            )
            if status:
                query = query.eq("status", status)

            result = await asyncio.to_thread(lambda: query.execute())
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_lead(row) for row in result.data]

    async def count_by_client(
        self, client_id: str, status: str | None = None
    ) -> int:
        try:
            query = (
                self._db.table(self.TABLE)
                .select("id")
                .eq("client_id", client_id)
            )
            if status:
                query = query.eq("status", status)

            result = await asyncio.to_thread(lambda: query.execute())
            return len(result.data)
        except Exception as exc:
            self._raise_domain_error(exc)
            return 0

    async def get_stats(self, client_id: str) -> dict:
        try:
            all_result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("id,status,score")
                .eq("client_id", client_id)
                .execute()
            )
            rows = all_result.data
            total = len(rows)

            by_status: dict[str, int] = {}
            scores: list[int] = []
            for row in rows:
                s = row["status"]
                by_status[s] = by_status.get(s, 0) + 1
                scores.append(row.get("score", 0))

            converted = by_status.get("converted", 0)
            conversion_rate = (converted / total * 100) if total > 0 else 0.0

            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            new_today_result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("id")
                .eq("client_id", client_id)
                .gte("created_at", today_start)
                .execute()
            )
            new_today = len(new_today_result.data)

            avg_score = sum(scores) / len(scores) if scores else 0.0

            return {
                "total": total,
                "by_status": by_status,
                "conversion_rate": round(conversion_rate, 2),
                "new_today": new_today,
                "avg_score": round(avg_score, 2),
            }
        except Exception as exc:
            self._raise_domain_error(exc)
            return {
                "total": 0,
                "by_status": {},
                "conversion_rate": 0.0,
                "new_today": 0,
                "avg_score": 0.0,
            }

    async def get_leads_new_today(self, client_id: str) -> list[Lead]:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .gte("created_at", today_start)
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_lead(row) for row in result.data]

    async def update_status_score(
        self, lead_id: str, status: str, score: int
    ) -> None:
        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .update({"status": status, "score": score, "updated_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", lead_id)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)

    @staticmethod
    def _row_to_lead(row: dict) -> Lead:
        lead = Lead(
            id=UUID(row["id"]),
            client_id=UUID(row["client_id"]),
            phone=row["phone"],
            name=row.get("name", ""),
            status=LeadStatus(row["status"]),
            source=row.get("source", "whatsapp"),
            score=row.get("score", 0),
            notes=row.get("notes", ""),
        )
        lead.created_at = datetime.fromisoformat(row["created_at"])
        lead.updated_at = datetime.fromisoformat(row["updated_at"])
        if row.get("last_contacted_at"):
            lead.last_contacted_at = datetime.fromisoformat(row["last_contacted_at"])
        return lead

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
