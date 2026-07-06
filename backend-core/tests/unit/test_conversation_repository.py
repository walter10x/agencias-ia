"""Unit tests for SupabaseConversationRepository — Fase 1 persistencia.

Fully mocked SupabaseHttpClient, no real network calls.
Covers the methods added for conversation persistence:
find_by_client_and_phone, save, append_message, get_recent_messages.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.domain.conversation.entity import Conversation, Message
from app.domain.shared.errors import DomainError
from app.infrastructure.persistence.conversation_repository import (
    SupabaseConversationRepository,
)

CLIENT_ID = "11111111-1111-1111-1111-111111111111"
AGENT_ID = "22222222-2222-2222-2222-222222222222"
CONV_ID = "33333333-3333-3333-3333-333333333333"
PHONE = "573001234567"


def _make_mock_chain() -> MagicMock:
    """Create a mock that returns itself for all chained method calls."""
    chain = MagicMock()
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.offset.return_value = chain
    chain.execute.return_value = chain
    return chain


def _make_conversation_row(**overrides: object) -> dict:
    row = {
        "id": CONV_ID,
        "client_id": CLIENT_ID,
        "agent_id": AGENT_ID,
        "wa_phone_number": PHONE,
        "status": "active",
        "created_at": "2026-07-01T10:00:00+00:00",
        "updated_at": "2026-07-01T10:00:00+00:00",
    }
    row.update(overrides)
    return row


def _make_message_row(**overrides: object) -> dict:
    row = {
        "id": "44444444-4444-4444-4444-444444444444",
        "conversation_id": CONV_ID,
        "role": "user",
        "content": "Hola",
        "tokens_used": 0,
        "status": "received",
        "created_at": "2026-07-01T10:00:00+00:00",
    }
    row.update(overrides)
    return row


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    table = MagicMock()
    chain = _make_mock_chain()
    table.select.return_value = chain
    table.insert.return_value = chain
    table.upsert.return_value = chain
    table.delete.return_value = chain
    db.table.return_value = table
    db._chain = chain
    db._table = table
    return db


@pytest.fixture
def repo(mock_db: MagicMock) -> SupabaseConversationRepository:
    return SupabaseConversationRepository(mock_db)


# ======================================================================
# find_by_client_and_phone()
# ======================================================================


@pytest.mark.asyncio
async def test_find_by_client_and_phone_returns_conversation(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.data = [_make_conversation_row()]

    found = await repo.find_by_client_and_phone(CLIENT_ID, PHONE)

    assert found is not None
    assert str(found.id) == CONV_ID
    assert str(found.client_id) == CLIENT_ID
    assert found.wa_phone_number == PHONE
    assert found.status == "active"
    # Filters by tenant AND phone
    mock_db._chain.eq.assert_any_call("client_id", CLIENT_ID)
    mock_db._chain.eq.assert_any_call("wa_phone_number", PHONE)
    # Takes the most recent conversation
    mock_db._chain.order.assert_called_once_with("updated_at", desc=True)
    mock_db._chain.limit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_find_by_client_and_phone_returns_none_when_missing(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.data = []

    found = await repo.find_by_client_and_phone(CLIENT_ID, PHONE)

    assert found is None


@pytest.mark.asyncio
async def test_find_by_client_and_phone_raises_domain_error_on_db_failure(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.execute.side_effect = RuntimeError("Supabase connection failed: boom")

    with pytest.raises(DomainError):
        await repo.find_by_client_and_phone(CLIENT_ID, PHONE)


# ======================================================================
# save()
# ======================================================================


@pytest.mark.asyncio
async def test_save_upserts_conversation_row(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    conv = Conversation(
        id=UUID(CONV_ID),
        client_id=UUID(CLIENT_ID),
        agent_id=UUID(AGENT_ID),
        wa_phone_number=PHONE,
    )

    await repo.save(conv)

    mock_db._table.upsert.assert_called_once()
    row = mock_db._table.upsert.call_args[0][0]
    assert row["id"] == CONV_ID
    assert row["client_id"] == CLIENT_ID
    assert row["agent_id"] == AGENT_ID
    assert row["wa_phone_number"] == PHONE
    assert row["status"] == "active"
    assert "created_at" in row and "updated_at" in row
    assert mock_db._table.upsert.call_args.kwargs.get("on_conflict") == "id"


@pytest.mark.asyncio
async def test_save_serializes_null_agent_id(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    conv = Conversation(
        id=UUID(CONV_ID),
        client_id=UUID(CLIENT_ID),
        agent_id=None,
        wa_phone_number=PHONE,
    )

    await repo.save(conv)

    row = mock_db._table.upsert.call_args[0][0]
    assert row["agent_id"] is None


@pytest.mark.asyncio
async def test_save_raises_domain_error_on_db_failure(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.execute.side_effect = RuntimeError("Supabase error: timeout")
    conv = Conversation(client_id=UUID(CLIENT_ID), wa_phone_number=PHONE)

    with pytest.raises(DomainError):
        await repo.save(conv)


# ======================================================================
# append_message()
# ======================================================================


@pytest.mark.asyncio
async def test_append_message_inserts_row_with_status(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    msg = Message(
        conversation_id=UUID(CONV_ID),
        role="user",
        content="Hola, quiero una cita",
        status="received",
    )

    await repo.append_message(msg)

    mock_db._table.insert.assert_called_once()
    row = mock_db._table.insert.call_args[0][0]
    assert row["conversation_id"] == CONV_ID
    assert row["role"] == "user"
    assert row["content"] == "Hola, quiero una cita"
    assert row["status"] == "received"
    assert row["tokens_used"] == 0
    assert "created_at" in row


@pytest.mark.asyncio
async def test_append_message_persists_assistant_send_status(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    msg = Message(
        conversation_id=UUID(CONV_ID),
        role="assistant",
        content="Claro, ¿a qué hora?",
        status="failed",
    )

    await repo.append_message(msg)

    row = mock_db._table.insert.call_args[0][0]
    assert row["role"] == "assistant"
    assert row["status"] == "failed"


@pytest.mark.asyncio
async def test_append_message_raises_domain_error_on_db_failure(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.execute.side_effect = RuntimeError("Supabase error: boom")
    msg = Message(conversation_id=UUID(CONV_ID), role="user", content="Hola")

    with pytest.raises(DomainError):
        await repo.append_message(msg)


# ======================================================================
# get_recent_messages()
# ======================================================================


@pytest.mark.asyncio
async def test_get_recent_messages_returns_ascending_order(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    # Supabase devuelve DESC (más reciente primero); el repo invierte a ASC
    mock_db._chain.data = [
        _make_message_row(
            id="66666666-6666-6666-6666-666666666666",
            role="assistant",
            content="¡Hola! ¿En qué te ayudo?",
            created_at="2026-07-01T10:01:00+00:00",
        ),
        _make_message_row(
            id="55555555-5555-5555-5555-555555555555",
            role="user",
            content="Hola",
            created_at="2026-07-01T10:00:00+00:00",
        ),
    ]

    messages = await repo.get_recent_messages(CONV_ID, limit=10)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hola"
    assert messages[1].role == "assistant"
    assert messages[1].content == "¡Hola! ¿En qué te ayudo?"
    # Pide los últimos N en DESC
    mock_db._chain.order.assert_called_once_with("created_at", desc=True)
    mock_db._chain.limit.assert_called_once_with(10)
    mock_db._chain.eq.assert_any_call("conversation_id", CONV_ID)


@pytest.mark.asyncio
async def test_get_recent_messages_respects_limit(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.data = []

    await repo.get_recent_messages(CONV_ID, limit=5)

    mock_db._chain.limit.assert_called_once_with(5)


@pytest.mark.asyncio
async def test_get_recent_messages_returns_empty_list(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.data = []

    messages = await repo.get_recent_messages(CONV_ID)

    assert messages == []


@pytest.mark.asyncio
async def test_get_recent_messages_defaults_status_for_legacy_rows(
    repo: SupabaseConversationRepository, mock_db: MagicMock
) -> None:
    """Filas anteriores a la migración 004 (sin columna status) → 'received'."""
    row = _make_message_row()
    del row["status"]
    mock_db._chain.data = [row]

    messages = await repo.get_recent_messages(CONV_ID)

    assert messages[0].status == "received"
