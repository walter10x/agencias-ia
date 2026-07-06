"""Tests for Conversation and Message domain entities (RED phase — TDD).

These tests import entity classes that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: Conversation creation/validation, Message creation/validation,
status transitions, equality, and ConversationStatus enum.
"""

from __future__ import annotations

from uuid import UUID

import pytest

# --- Domain entities (do NOT exist yet — RED phase) ---
from app.domain.conversation.entity import Conversation, Message, ConversationStatus


# ============================================================================
# Conversation entity — creation & validation
# ============================================================================


class TestConversationCreation:
    """Happy path: Conversation created with minimum valid data."""

    def test_creates_with_minimum_data(self) -> None:
        conv = Conversation(wa_phone_number="573001234567")

        assert conv.id is not None
        assert isinstance(conv.id, UUID)

        assert conv.client_id is not None
        assert isinstance(conv.client_id, UUID)

        assert conv.wa_phone_number == "573001234567"
        assert conv.status == "active"
        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert conv.last_message is None

    def test_sets_default_values(self) -> None:
        """Defaults: status='active', agent_id=None, last_message=None."""
        conv = Conversation(wa_phone_number="573001234567")
        assert conv.status == "active"
        assert conv.agent_id is None
        assert conv.last_message is None

    def test_accepts_all_fields(self) -> None:
        """All fields explicitly set at construction."""
        cid = UUID("11111111-1111-1111-1111-111111111111")
        client_id = UUID("22222222-2222-2222-2222-222222222222")
        agent_id = UUID("33333333-3333-3333-3333-333333333333")

        conv = Conversation(
            id=cid,
            client_id=client_id,
            agent_id=agent_id,
            wa_phone_number="573009876543",
            status="closed",
        )
        assert conv.id == cid
        assert conv.client_id == client_id
        assert conv.agent_id == agent_id
        assert conv.wa_phone_number == "573009876543"
        assert conv.status == "closed"

    def test_raises_on_empty_phone(self) -> None:
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            Conversation(wa_phone_number="")

    def test_raises_on_whitespace_only_phone(self) -> None:
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            Conversation(wa_phone_number="   ")

    def test_raises_on_invalid_status(self) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            Conversation(wa_phone_number="573001234567", status="deleted")

    def test_accepts_valid_statuses(self) -> None:
        for status in ("active", "closed", "archived"):
            conv = Conversation(wa_phone_number="573001234567", status=status)
            assert conv.status == status


# ============================================================================
# Conversation entity — status transitions
# ============================================================================


class TestConversationStatusChanges:
    """State machine: active → closed → archived transitions."""

    def test_close_changes_status_to_closed(self) -> None:
        conv = Conversation(wa_phone_number="573001234567")
        conv.close()
        assert conv.status == "closed"
        # updated_at should advance
        assert conv.updated_at is not None

    def test_archive_changes_status_to_archived(self) -> None:
        conv = Conversation(wa_phone_number="573001234567")
        conv.archive()
        assert conv.status == "archived"

    def test_reopen_activates_closed_conversation(self) -> None:
        conv = Conversation(wa_phone_number="573001234567", status="closed")
        conv.reopen()
        assert conv.status == "active"

    def test_reopen_activates_archived_conversation(self) -> None:
        conv = Conversation(wa_phone_number="573001234567", status="archived")
        conv.reopen()
        assert conv.status == "active"

    def test_reopen_does_nothing_on_already_active(self) -> None:
        conv = Conversation(wa_phone_number="573001234567", status="active")
        conv.reopen()
        assert conv.status == "active"


# ============================================================================
# Conversation entity — equality
# ============================================================================


class TestConversationEquality:
    """Conversation equality is based on id alone."""

    def test_same_id_are_equal(self) -> None:
        cid = UUID("11111111-1111-1111-1111-111111111111")
        a = Conversation(id=cid, wa_phone_number="573001234567")
        b = Conversation(id=cid, wa_phone_number="573009876543")
        assert a == b

    def test_different_id_not_equal(self) -> None:
        a = Conversation(wa_phone_number="573001234567")
        b = Conversation(wa_phone_number="573001234567")
        assert a != b

    def test_not_equal_to_non_conversation(self) -> None:
        conv = Conversation(wa_phone_number="573001234567")
        assert conv != "not-a-conversation"
        assert conv != 42
        assert conv is not None

    def test_hash_is_stable(self) -> None:
        cid = UUID("11111111-1111-1111-1111-111111111111")
        conv = Conversation(id=cid, wa_phone_number="573001234567")
        assert hash(conv) == hash(cid)


# ============================================================================
# ConversationStatus enum
# ============================================================================


class TestConversationStatusEnum:
    """ConversationStatus enum values match database CHECK constraint."""

    def test_enum_has_expected_values(self) -> None:
        assert ConversationStatus.ACTIVE.value == "active"
        assert ConversationStatus.CLOSED.value == "closed"
        assert ConversationStatus.ARCHIVED.value == "archived"

    def test_enum_values_are_strings(self) -> None:
        for status in ConversationStatus:
            assert isinstance(status.value, str)

    def test_enum_members_are_unique(self) -> None:
        values = [m.value for m in ConversationStatus]
        assert len(values) == len(set(values))

    def test_from_string_valid(self) -> None:
        assert ConversationStatus("active") == ConversationStatus.ACTIVE
        assert ConversationStatus("closed") == ConversationStatus.CLOSED
        assert ConversationStatus("archived") == ConversationStatus.ARCHIVED

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            ConversationStatus("deleted")


# ============================================================================
# Message entity — creation & validation
# ============================================================================


class TestMessageCreation:
    """Happy path: Message created with minimum valid data."""

    def test_creates_with_minimum_data(self) -> None:
        msg = Message(role="user", content="Hola, ¿qué tal?")

        assert msg.id is not None
        assert isinstance(msg.id, UUID)

        assert msg.conversation_id is not None
        assert isinstance(msg.conversation_id, UUID)

        assert msg.role == "user"
        assert msg.content == "Hola, ¿qué tal?"
        assert msg.tokens_used == 0
        assert msg.created_at is not None

    def test_accepts_all_valid_roles(self) -> None:
        for role in ("user", "assistant", "system"):
            msg = Message(role=role, content="test content")
            assert msg.role == role

    def test_accepts_all_fields(self) -> None:
        mid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        cid = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

        msg = Message(
            id=mid,
            conversation_id=cid,
            role="assistant",
            content="¡Claro! Tenemos disponibilidad.",
            tokens_used=25,
        )
        assert msg.id == mid
        assert msg.conversation_id == cid
        assert msg.role == "assistant"
        assert msg.content == "¡Claro! Tenemos disponibilidad."
        assert msg.tokens_used == 25

    def test_tokens_used_defaults_to_zero(self) -> None:
        msg = Message(role="user", content="Hello")
        assert msg.tokens_used == 0

    def test_allows_zero_tokens(self) -> None:
        msg = Message(role="user", content="Hello", tokens_used=0)
        assert msg.tokens_used == 0

    def test_raises_on_invalid_role(self) -> None:
        with pytest.raises(ValueError, match="Invalid role"):
            Message(role="admin", content="test")

    def test_raises_on_empty_content(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            Message(role="user", content="")

    def test_raises_on_whitespace_only_content(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            Message(role="user", content="   ")

    def test_raises_on_none_content(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            Message(role="user", content="")  # type: ignore[arg-type]


# ============================================================================
# Message entity — delivery status (Fase 1 persistencia)
# ============================================================================


class TestMessageStatus:
    """Estados de entrega: received (entrante), sent/failed/skipped (saliente)."""

    def test_defaults_to_received(self) -> None:
        msg = Message(role="user", content="Hola")
        assert msg.status == "received"

    def test_accepts_all_valid_statuses(self) -> None:
        for status in ("received", "sent", "failed", "skipped"):
            msg = Message(role="assistant", content="Respuesta", status=status)
            assert msg.status == status

    def test_raises_on_invalid_status(self) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            Message(role="assistant", content="Respuesta", status="delivered")
