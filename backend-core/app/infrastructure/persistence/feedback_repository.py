"""Supabase adapter for FeedbackRepository port (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.domain.feedback.entity import Feedback
from app.domain.feedback.repository import FeedbackRepository
from app.domain.shared.errors import DomainError
from app.infrastructure.http.supabase_client import SupabaseHttpClient


class SupabaseFeedbackRepository(FeedbackRepository):
    """Supabase implementation of FeedbackRepository."""

    TABLE = "feedback"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    async def save(self, feedback: Feedback) -> None:
        row = {
            "id": str(feedback.id),
            "client_id": str(feedback.client_id),
            "lead_id": str(feedback.lead_id) if feedback.lead_id else None,
            "conversation_id": str(feedback.conversation_id) if feedback.conversation_id else None,
            "rating": feedback.rating,
            "comment": feedback.comment,
            "created_at": feedback.created_at.isoformat(),
        }
        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .insert(row)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)

    async def list_by_client(
        self,
        client_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Feedback]:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", client_id)
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_feedback(row) for row in result.data]

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
                .select("rating")
                .eq("client_id", client_id)
                .execute()
            )
            ratings = [row["rating"] for row in result.data]
            total = len(ratings)

            rating_distribution: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for r in ratings:
                rating_distribution[r] = rating_distribution.get(r, 0) + 1

            average_rating = sum(ratings) / total if total > 0 else 0.0

            return {
                "total": total,
                "average_rating": round(average_rating, 2),
                "rating_distribution": rating_distribution,
            }
        except Exception as exc:
            self._raise_domain_error(exc)
            return {
                "total": 0,
                "average_rating": 0.0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            }

    @staticmethod
    def _row_to_feedback(row: dict) -> Feedback:
        fb = Feedback(
            id=UUID(row["id"]),
            client_id=UUID(row["client_id"]),
            lead_id=UUID(row["lead_id"]) if row.get("lead_id") else None,
            conversation_id=UUID(row["conversation_id"]) if row.get("conversation_id") else None,
            rating=row["rating"],
            comment=row.get("comment", ""),
        )
        fb.created_at = row.get("created_at")
        return fb

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
