"""Supabase adapter for AgentRepository port (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from app.infrastructure.http.supabase_client import SupabaseHttpClient

from app.domain.agent.entity import Agent, AgentTool
from app.domain.agent.repository import AgentRepository
from app.domain.shared.errors import AgentNotFoundError, DomainError, InvalidAgentError
from app.domain.shared.value_objects import AgentId, ClientId


class SupabaseAgentRepository(AgentRepository):
    """Supabase implementation of AgentRepository.

    Uses supabase-py sync client wrapped in asyncio.to_thread.
    Tools are serialized as JSONB, knowledge_base_refs as TEXT[].
    """

    TABLE = "agents"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    # ------------------------------------------------------------------
    # Port methods
    # ------------------------------------------------------------------

    async def save(self, agent: Agent) -> None:
        """Insert or update an Agent (UPSERT by id)."""
        row = self._agent_to_row(agent)
        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .upsert(row, on_conflict="id")
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)

    async def find_by_id(self, agent_id: AgentId) -> Optional[Agent]:
        """Find an agent by its AgentId. Returns None if not found."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("id", str(agent_id))
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return None

        if not result.data:
            return None
        return self._row_to_agent(result.data[0])

    async def find_active_by_client(self, client_id: ClientId) -> list[Agent]:
        """Return all active agents belonging to a client."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("client_id", str(client_id))
                .eq("is_active", True)
                .order("created_at", desc=False)
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return []

        return [self._row_to_agent(row) for row in result.data]

    async def delete(self, agent_id: AgentId) -> None:
        """Delete an agent by id. Raises AgentNotFoundError if not found."""
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .delete()
                .eq("id", str(agent_id))
                .execute()
            )
        except Exception as exc:
            self._raise_domain_error(exc)
            return

        if not result.data:
            raise AgentNotFoundError(
                f"Agent not found: {agent_id}"
            )

    # ------------------------------------------------------------------
    # Private mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _agent_to_row(agent: Agent) -> dict:
        """Map an Agent entity to a Supabase row dict (tools → JSONB)."""
        return {
            "id": str(agent.id),
            "client_id": str(agent.client_id),
            "name": agent.name,
            "personality": agent.personality,
            "tools": [
                {"name": t.name, "description": t.description, "endpoint": t.endpoint}
                for t in agent.tools
            ],
            "knowledge_base_refs": agent.knowledge_base_refs,
            "is_active": agent.is_active,
            "created_at": agent.created_at.isoformat(),
            "updated_at": agent.updated_at.isoformat(),
        }

    @staticmethod
    def _row_to_agent(row: dict) -> Agent:
        """Reconstruct an Agent entity from a Supabase row dict (JSONB → tools)."""
        tools_raw = row.get("tools") or []
        agent = Agent(
            id=UUID(row["id"]),
            client_id=ClientId(UUID(row["client_id"])),
            name=row["name"],
            personality=row["personality"],
            tools=[AgentTool(**t) for t in tools_raw],
            knowledge_base_refs=row.get("knowledge_base_refs", []),
            is_active=row["is_active"],
        )
        agent.created_at = datetime.fromisoformat(row["created_at"])
        agent.updated_at = datetime.fromisoformat(row["updated_at"])
        return agent

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_domain_error(exc: Exception) -> None:
        """Map infrastructure exceptions to domain errors."""
        import json

        message = str(exc)

        # El código PostgreSQL puede venir como atributo de la excepción
        # (drivers/SDKs que lo exponen) o embebido en el body PostgREST
        # ("Supabase error: {json}"). Se prueban ambas fuentes.
        pg_code = str(getattr(exc, "code", "") or "")
        try:
            if "Supabase error:" in message:
                body_str = message.split("Supabase error:", 1)[1].strip()
                body = json.loads(body_str)
                pg_code = body.get("code", "") or pg_code
                message = body.get("message", message)
        except (json.JSONDecodeError, IndexError):
            pass

        # PostgreSQL foreign_key_violation (23503) → invalid client_id
        if pg_code == "23503":
            raise InvalidAgentError(
                f"Invalid client_id or foreign key violation: {message}"
            ) from exc

        # Connection / timeout errors
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            raise DomainError("Database connection failed") from exc
        if "connection" in message.lower() or "timeout" in message.lower():
            raise DomainError("Database connection failed") from exc

        raise DomainError(f"Database error: {message}") from exc
