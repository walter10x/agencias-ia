"""Supabase implementation of LandingRepository (DRIVEN ADAPTER)."""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.domain.client.entity import Client
from app.domain.landing.repository import LandingConfig, LandingRepository
from app.domain.shared.value_objects import BusinessType, WhatsAppNumber
from app.infrastructure.http.supabase_client import SupabaseHttpClient


class SupabaseLandingRepository(LandingRepository):
    """Adaptador Supabase para operaciones de landing page."""

    TABLE = "clients"
    SUBMISSIONS_TABLE = "landing_submissions"

    def __init__(self, client: SupabaseHttpClient) -> None:
        self._db = client

    async def find_client_by_slug(self, slug: str) -> tuple[Client, LandingConfig] | None:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("landing_slug", slug)
                .execute()
            )
        except Exception:
            return None

        if not result.data:
            return None

        row = result.data[0]
        client = Client(
            id=UUID(row["id"]),
            name=row["name"],
            business_type=BusinessType(row.get("business_type", "otro")),
            whatsapp_number=WhatsAppNumber(row.get("whatsapp_number", "0000000000")),
            is_active=row.get("is_active", True),
        )
        config = LandingConfig(
            client_id=row["id"],
            slug=row.get("landing_slug") or "",
            title=row.get("landing_title") or "Impulsa tu negocio con IA",
            description=row.get("landing_description") or "Déjanos tus datos y te contactamos",
            is_active=row.get("landing_active") or False,
            primary_color=row.get("landing_primary_color") or "#f59e0b",
            auto_reply=row.get("landing_auto_reply") or "¡Hola {{name}}! Gracias por contactarnos.",
        )
        return client, config

    async def get_landing_config(self, client_id: str) -> LandingConfig | None:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("id", "landing_slug", "landing_title", "landing_description",
                         "landing_active", "landing_primary_color", "landing_auto_reply")
                .eq("id", client_id)
                .execute()
            )
        except Exception:
            return None

        if not result.data:
            return None

        row = result.data[0]
        return LandingConfig(
            client_id=row["id"],
            slug=row.get("landing_slug") or "",
            title=row.get("landing_title") or "Impulsa tu negocio con IA",
            description=row.get("landing_description") or "Déjanos tus datos y te contactamos",
            is_active=row.get("landing_active") or False,
            primary_color=row.get("landing_primary_color") or "#f59e0b",
            auto_reply=row.get("landing_auto_reply") or "¡Hola {{name}}! Gracias por contactarnos.",
        )

    async def update_landing_config(self, client_id: str, data) -> LandingConfig:
        update_data = {}
        if data.landing_slug is not None:
            update_data["landing_slug"] = data.landing_slug
        if data.landing_title is not None:
            update_data["landing_title"] = data.landing_title
        if data.landing_description is not None:
            update_data["landing_description"] = data.landing_description
        if data.landing_active is not None:
            update_data["landing_active"] = data.landing_active
        if data.landing_primary_color is not None:
            update_data["landing_primary_color"] = data.landing_primary_color
        if data.landing_auto_reply is not None:
            update_data["landing_auto_reply"] = data.landing_auto_reply

        if update_data:
            await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .update(update_data)
                .eq("id", client_id)
                .execute()
            )

        config = await self.get_landing_config(client_id)
        if config is None:
            raise RuntimeError(f"Client {client_id} not found after update")
        return config

    async def slug_exists(self, slug: str, exclude_client_id: str | None = None) -> bool:
        try:
            query = self._db.table(self.TABLE).select("id").eq("landing_slug", slug)
            if exclude_client_id:
                query = query.neq("id", exclude_client_id)
            result = await asyncio.to_thread(lambda: query.execute())
        except Exception:
            return False

        return len(result.data) > 0

    async def count_leads_by_landing(self, client_id: str) -> int:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table("leads")
                .select("id")
                .eq("client_id", client_id)
                .eq("source", "landing")
                .execute()
            )
        except Exception:
            return 0

        return result.count if result.count is not None else len(result.data)

    async def check_rate_limit(self, ip: str, max_req: int = 5, window_sec: int = 60) -> bool:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.SUBMISSIONS_TABLE)
                .select("id")
                .gte("created_at", f"now() - interval '{window_sec} seconds'")
                .eq("ip_address", ip)
                .execute()
            )
        except Exception:
            return True

        count = result.count if result.count is not None else len(result.data)
        if count >= max_req:
            return False

        try:
            await asyncio.to_thread(
                lambda: self._db.table(self.SUBMISSIONS_TABLE)
                .insert({"ip_address": ip, "created_at": "now()"})
                .execute()
            )
        except Exception:
            pass

        return True

    async def get_all_slugs(self) -> set[str]:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("landing_slug")
                .execute()
            )
        except Exception:
            return set()

        slugs = set()
        for row in result.data:
            if row.get("landing_slug"):
                slugs.add(row["landing_slug"])
        return slugs

    async def get_client(self, client_id: str) -> Client | None:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self.TABLE)
                .select("*")
                .eq("id", client_id)
                .execute()
            )
        except Exception:
            return None

        if not result.data:
            return None

        row = result.data[0]
        return Client(
            id=UUID(row["id"]),
            name=row["name"],
            business_type=BusinessType(row.get("business_type", "otro")),
            whatsapp_number=WhatsAppNumber(row.get("whatsapp_number", "0000000000")),
            is_active=row.get("is_active", True),
        )
