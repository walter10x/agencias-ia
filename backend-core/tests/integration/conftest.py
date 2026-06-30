"""Shared fixtures for Supabase integration tests.

These tests run against a real Supabase instance.
Requires .env with SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from uuid import UUID

import pytest
from supabase import Client as SupabaseClient
from supabase import create_client

from app.domain.agent.entity import Agent, AgentTool
from app.domain.client.entity import Client
from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository  # type: ignore[import-untyped]  # noqa: E501
from app.infrastructure.persistence.client_repository import SupabaseClientRepository  # type: ignore[import-untyped]  # noqa: E501

# -- Fixed UUIDs for deterministic, repeatable tests --

SAMPLE_CLIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
SAMPLE_AGENT_ID = UUID("22222222-2222-2222-2222-222222222222")
INACTIVE_AGENT_ID = UUID("33333333-3333-3333-3333-333333333333")
SECOND_CLIENT_ID = UUID("44444444-4444-4444-4444-444444444444")
DUMMY_UUID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Event loop (session-scoped, required by pytest-asyncio)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create a fresh event loop shared across the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Supabase real client (session-scoped → one connection for all tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def supabase_client() -> SupabaseClient:
    """Real Supabase client reading credentials from .env."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        pytest.skip(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env — "
            "skipping integration tests"
        )
    if "your-project" in settings.supabase_url or "your-service-role-key" in settings.supabase_service_key:
        pytest.skip(
            "Placeholder Supabase credentials detected in .env — "
            "skipping integration tests"
        )
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ---------------------------------------------------------------------------
# DB cleanup (autouse → every test starts and ends with clean tables)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def clean_db(supabase_client: SupabaseClient) -> AsyncGenerator[None, None]:
    """Delete all rows from agents then clients before AND after each test."""
    # -- Pre-test cleanup ---------------------------------------------------
    await _delete_all(supabase_client, "agents")
    await _delete_all(supabase_client, "clients")

    yield

    # -- Post-test cleanup --------------------------------------------------
    await _delete_all(supabase_client, "agents")
    await _delete_all(supabase_client, "clients")


async def _delete_all(client: SupabaseClient, table: str) -> None:
    """Helper: delete every row from *table* using the sync client."""
    # PostgREST requires a filter on DELETE; .neq() against a dummy id
    # deletes every real row.
    await asyncio.to_thread(
        lambda: client.table(table)
        .delete()
        .neq("id", DUMMY_UUID)
        .execute()
    )


# ---------------------------------------------------------------------------
# Repository instances (function-scoped — fresh per test)
# ---------------------------------------------------------------------------

@pytest.fixture
def client_repo(supabase_client: SupabaseClient) -> SupabaseClientRepository:
    """SupabaseClientRepository wired to the real Supabase client."""
    return SupabaseClientRepository(supabase_client)


@pytest.fixture
def agent_repo(supabase_client: SupabaseClient) -> SupabaseAgentRepository:
    """SupabaseAgentRepository wired to the real Supabase client."""
    return SupabaseAgentRepository(supabase_client)


# ---------------------------------------------------------------------------
# Sample entities (function-scoped — every test gets a clean copy)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_client() -> Client:
    """A pre-built Client entity with fixed, valid data (NOT yet persisted)."""
    return Client(
        id=SAMPLE_CLIENT_ID,
        name="Peluqueria El Buen Corte",
        business_type=BusinessType("peluqueria"),
        whatsapp_number=WhatsAppNumber("573001111111"),
    )


@pytest.fixture
def sample_agent(sample_client: Client) -> Agent:
    """A pre-built Agent entity linked to sample_client, with tools.

    Requires the parent client to be saved first in any test that saves
    this agent.
    """
    return Agent(
        id=SAMPLE_AGENT_ID,
        client_id=ClientId(value=sample_client.id),
        name="Bot Peluquería",
        personality="Eres un asistente amable de una peluquería. "
        "Ayudas a agendar citas y responder preguntas frecuentes.",
        tools=[
            AgentTool(
                name="agendar_cita",
                description="Agenda una cita en el calendario del negocio",
                endpoint="https://n8n.example.com/webhook/agendar",
            ),
            AgentTool(
                name="consultar_precios",
                description="Consulta los precios de los servicios disponibles",
                endpoint="https://n8n.example.com/webhook/precios",
            ),
        ],
        knowledge_base_refs=[
            "kb-peluqueria-servicios",
            "kb-peluqueria-precios",
        ],
    )
