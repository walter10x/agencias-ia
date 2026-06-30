"""Supabase adapter for ConversationRepository port (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.domain.conversation.entity import Conversation, Message
from app.domain.conversation.repository import ConversationRepository
from app.domain.shared.errors import ConversationNotFoundError, DomainError
from app.infrastructure.http.supabase_client import SupabaseHttpClient


class SupabaseConversationRepository(ConversationRepository):
    """Supabase implementation of ConversationRepository."""

    CONV_TABLE = "conversations"
    MSG_TABLE = "messages"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    # ------------------------------------------------------------------
    # Port methods
    # ------------------------------------------------------------------

    async def list_by_client(
        self,
        client_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations with last message preview."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.CONV_TABLE)
                .select("*")
                .eq("client_id", client_id)
                .order("updated_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        conversations = []
        for row in result.data:
            conv = self._row_to_conversation(row)
            # Fetch last message for preview
            conv.last_message = await self._get_last_message(str(conv.id))
            conversations.append(conv)

        return conversations

    async def count_by_client(self, client_id: str) -> int:
        """Count conversations for a client."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.CONV_TABLE)
                .select("id")
                .eq("client_id", client_id)
                .execute()
            )
            return len(result.data)
        except Exception as exc:
            self._raise_domain_error(exc)
            return 0

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Get all messages for a conversation, ordered by created_at ASC."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.MSG_TABLE)
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=False)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_message(row) for row in result.data]

    async def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Find a conversation by ID."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.CONV_TABLE)
                .select("*")
                .eq("id", conversation_id)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_conversation(result.data[0])

    async def get_stats(self) -> dict:
        """Get global conversation statistics."""
        try:
            # Total conversations
            total_result = await asyncio.to_thread(
                lambda: self._db.table(self.CONV_TABLE)
                .select("id")
                .execute()
            )
            total = len(total_result.data)

            # Active conversations
            active_result = await asyncio.to_thread(
                lambda: self._db.table(self.CONV_TABLE)
                .select("id")
                .eq("status", "active")
                .execute()
            )
            active = len(active_result.data)

            # Messages today
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            msgs_result = await asyncio.to_thread(
                lambda: self._db.table(self.MSG_TABLE)
                .select("id")
                .gte("created_at", today_start)
                .execute()
            )
            msgs_today = len(msgs_result.data)

            # Unique clients with conversations
            clients_result = await asyncio.to_thread(
                lambda: self._db.table(self.CONV_TABLE)
                .select("client_id")
                .execute()
            )
            unique_clients = len({row["client_id"] for row in clients_result.data})

            return {
                "total_conversations": total,
                "active_conversations": active,
                "messages_today": msgs_today,
                "clients_with_conversations": unique_clients,
            }

        except Exception as exc:
            self._raise_domain_error(exc)
            return {
                "total_conversations": 0,
                "active_conversations": 0,
                "messages_today": 0,
                "clients_with_conversations": 0,
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_last_message(self, conversation_id: str) -> Optional[str]:
        """Get the content of the most recent message in a conversation."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.MSG_TABLE)
                .select("content")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]["content"]
            return None
        except Exception:
            return None

    @staticmethod
    def _row_to_conversation(row: dict) -> Conversation:
        """Reconstruct a Conversation entity from a Supabase row dict."""
        conv = Conversation(
            id=UUID(row["id"]),
            client_id=UUID(row["client_id"]),
            agent_id=UUID(row["agent_id"]) if row.get("agent_id") else None,
            wa_phone_number=row["wa_phone_number"],
            status=row["status"],
        )
        conv.created_at = datetime.fromisoformat(row["created_at"])
        conv.updated_at = datetime.fromisoformat(row["updated_at"])
        return conv

    @staticmethod
    def _row_to_message(row: dict) -> Message:
        """Reconstruct a Message entity from a Supabase row dict."""
        msg = Message(
            id=UUID(row["id"]),
            conversation_id=UUID(row["conversation_id"]),
            role=row["role"],
            content=row["content"],
            tokens_used=row.get("tokens_used", 0),
        )
        msg.created_at = datetime.fromisoformat(row["created_at"])
        return msg

    @staticmethod
    def _raise_domain_error(exc: Exception) -> None:
        """Map infrastructure exceptions to domain errors."""
        import json

        import httpx

        message = str(exc)

        pg_code = ""
        try:
            if "Supabase error:" in message:
                body_str = message.split("Supabase error:", 1)[1].strip()
                body = json.loads(body_str)
                pg_code = body.get("code", "")
                message = body.get("message", message)
        except (json.JSONDecodeError, IndexError):
            pass

        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            raise DomainError("Database connection failed") from exc
        if "connection" in message.lower() or "timeout" in message.lower():
            raise DomainError("Database connection failed") from exc

        raise DomainError(f"Database error: {message}") from exc
