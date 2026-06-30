"""Unit tests for Conversation application use cases (RED phase — TDD).

These tests import use case classes, DTOs, and repository ports that
do NOT exist yet. They define the expected behavior before any
implementation is written.

Coverage: ListConversationsUseCase, GetConversationMessagesUseCase,
GetConversationStatsUseCase.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.conversation.get_conversation_messages import (
    GetConversationMessagesUseCase,
)
from app.application.conversation.get_conversation_stats import (
    GetConversationStatsUseCase,
)
from app.application.conversation.list_conversations import ListConversationsUseCase
from app.application.dtos import (
    ConversationOutput,
    ConversationStatsOutput,
    GetConversationMessagesInput,
    ListConversationsInput,
    MessageOutput,
)

# --- Domain layer (does NOT exist yet for conversation — RED phase) ---
from app.domain.conversation.entity import Conversation, Message
from app.domain.conversation.repository import ConversationRepository
from app.domain.shared.errors import ConversationNotFoundError


# ============================================================================
# Helpers
# ============================================================================


def _make_conversation(**overrides: object) -> Conversation:
    """Factory for Conversation entities with overridable fields.

    Creates a valid Conversation with defaults, then applies overrides
    via object.__setattr__ for frozen/dataclass-managed fields.
    Timestamps default to 2026-01-01 UTC.
    """
    conv = Conversation(
        wa_phone_number=str(overrides.get("wa_phone_number", "573001234567")),
        status=str(overrides.get("status", "active")),
    )
    if "id" in overrides:
        object.__setattr__(conv, "id", overrides["id"])
    if "client_id" in overrides:
        object.__setattr__(conv, "client_id", overrides["client_id"])
    if "agent_id" in overrides:
        object.__setattr__(conv, "agent_id", overrides["agent_id"])
    if "last_message" in overrides:
        val = overrides["last_message"]
        conv.last_message = str(val) if val is not None else None
    if "created_at" in overrides:
        object.__setattr__(conv, "created_at", overrides["created_at"])
    else:
        object.__setattr__(conv, "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    if "updated_at" in overrides:
        object.__setattr__(conv, "updated_at", overrides["updated_at"])
    else:
        object.__setattr__(conv, "updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    return conv


def _make_message(**overrides: object) -> Message:
    """Factory for Message entities with overridable fields."""
    msg = Message(
        role=str(overrides.get("role", "user")),
        content=str(overrides.get("content", "Hello")),
        tokens_used=int(overrides.get("tokens_used", 0)),
    )
    if "id" in overrides:
        object.__setattr__(msg, "id", overrides["id"])
    if "conversation_id" in overrides:
        object.__setattr__(msg, "conversation_id", overrides["conversation_id"])
    if "created_at" in overrides:
        object.__setattr__(msg, "created_at", overrides["created_at"])
    else:
        object.__setattr__(msg, "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    return msg


# ============================================================================
# ListConversationsUseCase
# ============================================================================


class TestListConversationsUseCase:
    """Happy path: returns paginated results, filters by client_id,
    returns empty list, validates client_id input.
    """

    @pytest.mark.asyncio
    async def test_returns_paginated_results(self) -> None:
        """Happy path: valid input → list[ConversationOutput] + total count."""
        conversations = [
            _make_conversation(
                id=uuid.uuid4(),
                wa_phone_number=f"57300{i:06d}",
                last_message=f"Message {i}",
            )
            for i in range(3)
        ]
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.list_by_client.return_value = conversations
        mock_repo.count_by_client.return_value = 3

        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id=str(uuid.uuid4()), limit=20, offset=0)

        outputs, total = await uc.execute(inp)

        assert total == 3
        assert len(outputs) == 3
        assert all(isinstance(o, ConversationOutput) for o in outputs)
        assert outputs[0].wa_phone_number == "57300000000"
        assert outputs[0].last_message == "Message 0"
        mock_repo.list_by_client.assert_awaited_once()
        mock_repo.count_by_client.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_filters_by_client_id(self) -> None:
        """Passes client_id, limit, offset to the repository."""
        client_id = str(uuid.uuid4())
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.list_by_client.return_value = []
        mock_repo.count_by_client.return_value = 0

        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id=client_id, limit=10, offset=5)

        await uc.execute(inp)

        mock_repo.list_by_client.assert_awaited_once_with(
            client_id=client_id,
            limit=10,
            offset=5,
        )
        mock_repo.count_by_client.assert_awaited_once_with(client_id=client_id)

    @pytest.mark.asyncio
    async def test_returns_empty_list(self) -> None:
        """No conversations for the given client → ([], 0)."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.list_by_client.return_value = []
        mock_repo.count_by_client.return_value = 0

        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id=str(uuid.uuid4()))

        outputs, total = await uc.execute(inp)

        assert outputs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_raises_on_empty_client_id(self) -> None:
        """Blank string client_id → ValueError before touching repo."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id="")

        with pytest.raises(ValueError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.list_by_client.assert_not_awaited()
        mock_repo.count_by_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_whitespace_client_id(self) -> None:
        """Whitespace-only client_id → ValueError."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id="   ")

        with pytest.raises(ValueError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.list_by_client.assert_not_awaited()
        mock_repo.count_by_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_uses_default_pagination(self) -> None:
        """Default limit=20, offset=0 when not provided in DTO."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.list_by_client.return_value = []
        mock_repo.count_by_client.return_value = 0

        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id=str(uuid.uuid4()))

        await uc.execute(inp)

        mock_repo.list_by_client.assert_awaited_once_with(
            client_id=inp.client_id,
            limit=20,
            offset=0,
        )

    @pytest.mark.asyncio
    async def test_output_maps_all_fields(self) -> None:
        """Conversation entity fields are correctly mapped to ConversationOutput."""
        cid = uuid.uuid4()
        client_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        created = datetime(2026, 6, 10, 14, 30, tzinfo=timezone.utc)
        updated = datetime(2026, 6, 11, 9, 15, tzinfo=timezone.utc)

        conv = _make_conversation(
            id=cid,
            client_id=client_id,
            agent_id=agent_id,
            wa_phone_number="573001234567",
            status="active",
            last_message="Hola, ¿tienen disponibilidad?",
            created_at=created,
            updated_at=updated,
        )
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.list_by_client.return_value = [conv]
        mock_repo.count_by_client.return_value = 1

        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id=str(client_id))

        outputs, total = await uc.execute(inp)

        output = outputs[0]
        assert output.id == str(cid)
        assert output.client_id == str(client_id)
        assert output.agent_id == str(agent_id)
        assert output.wa_phone_number == "573001234567"
        assert output.status == "active"
        assert output.last_message == "Hola, ¿tienen disponibilidad?"
        assert output.created_at == "2026-06-10T14:30:00+00:00"
        assert output.updated_at == "2026-06-11T09:15:00+00:00"

    @pytest.mark.asyncio
    async def test_output_allows_null_agent_id(self) -> None:
        """When agent_id is None, ConversationOutput.agent_id is None."""
        conv = _make_conversation(agent_id=None)
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.list_by_client.return_value = [conv]
        mock_repo.count_by_client.return_value = 1

        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id=str(uuid.uuid4()))

        outputs, total = await uc.execute(inp)

        assert outputs[0].agent_id is None

    @pytest.mark.asyncio
    async def test_output_allows_null_last_message(self) -> None:
        """When last_message is None, ConversationOutput.last_message is None."""
        conv = _make_conversation(last_message=None)
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.list_by_client.return_value = [conv]
        mock_repo.count_by_client.return_value = 1

        uc = ListConversationsUseCase(mock_repo)
        inp = ListConversationsInput(client_id=str(uuid.uuid4()))

        outputs, total = await uc.execute(inp)

        assert outputs[0].last_message is None


# ============================================================================
# GetConversationMessagesUseCase
# ============================================================================


class TestGetConversationMessagesUseCase:
    """Happy path: messages ordered, not found, invalid UUID, empty messages."""

    CONVERSATION_ID = "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_returns_messages_ordered(self) -> None:
        """Happy path: valid conversation → (messages, phone, status)."""
        messages = [
            _make_message(
                id=uuid.uuid4(),
                conversation_id=uuid.UUID(self.CONVERSATION_ID),
                role="user",
                content="Hola",
                created_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            ),
            _make_message(
                id=uuid.uuid4(),
                conversation_id=uuid.UUID(self.CONVERSATION_ID),
                role="assistant",
                content="¡Hola!",
                created_at=datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc),
            ),
        ]
        conv = _make_conversation(
            id=uuid.UUID(self.CONVERSATION_ID),
            wa_phone_number="573001234567",
            status="active",
        )
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.find_by_id.return_value = conv
        mock_repo.get_messages.return_value = messages

        uc = GetConversationMessagesUseCase(mock_repo)
        inp = GetConversationMessagesInput(conversation_id=self.CONVERSATION_ID)

        msg_outputs, phone_number, status = await uc.execute(inp)

        assert len(msg_outputs) == 2
        assert all(isinstance(m, MessageOutput) for m in msg_outputs)
        assert msg_outputs[0].role == "user"
        assert msg_outputs[0].content == "Hola"
        assert msg_outputs[1].role == "assistant"
        assert msg_outputs[1].content == "¡Hola!"
        assert phone_number == "573001234567"
        assert status == "active"
        mock_repo.find_by_id.assert_awaited_once_with(self.CONVERSATION_ID)
        mock_repo.get_messages.assert_awaited_once_with(self.CONVERSATION_ID)

    @pytest.mark.asyncio
    async def test_raises_on_not_found(self) -> None:
        """Non-existent conversation_id → ConversationNotFoundError."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.find_by_id.return_value = None

        uc = GetConversationMessagesUseCase(mock_repo)
        inp = GetConversationMessagesInput(conversation_id=self.CONVERSATION_ID)

        with pytest.raises(ConversationNotFoundError, match="not found"):
            await uc.execute(inp)

        mock_repo.get_messages.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_uuid(self) -> None:
        """Non-UUID conversation_id → ConversationNotFoundError."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        uc = GetConversationMessagesUseCase(mock_repo)
        inp = GetConversationMessagesInput(conversation_id="not-a-uuid")

        with pytest.raises(ConversationNotFoundError, match="Invalid conversation ID"):
            await uc.execute(inp)

        mock_repo.find_by_id.assert_not_awaited()
        mock_repo.get_messages.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_empty_conversation_id(self) -> None:
        """Empty string conversation_id → ConversationNotFoundError."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        uc = GetConversationMessagesUseCase(mock_repo)
        inp = GetConversationMessagesInput(conversation_id="")

        with pytest.raises(ConversationNotFoundError, match="Invalid conversation ID"):
            await uc.execute(inp)

        mock_repo.find_by_id.assert_not_awaited()
        mock_repo.get_messages.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_empty_messages(self) -> None:
        """Conversation exists but has no messages → ([], phone, status)."""
        conv = _make_conversation(
            id=uuid.UUID(self.CONVERSATION_ID),
            wa_phone_number="573001234567",
            status="closed",
        )
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.find_by_id.return_value = conv
        mock_repo.get_messages.return_value = []

        uc = GetConversationMessagesUseCase(mock_repo)
        inp = GetConversationMessagesInput(conversation_id=self.CONVERSATION_ID)

        msg_outputs, phone_number, status = await uc.execute(inp)

        assert msg_outputs == []
        assert phone_number == "573001234567"
        assert status == "closed"

    @pytest.mark.asyncio
    async def test_output_maps_message_fields(self) -> None:
        """Message entity fields are correctly mapped to MessageOutput."""
        mid = uuid.uuid4()
        cid = uuid.UUID(self.CONVERSATION_ID)
        created = datetime(2026, 6, 10, 14, 30, 0, tzinfo=timezone.utc)

        msg = _make_message(
            id=mid,
            conversation_id=cid,
            role="user",
            content="Hola, ¿tienen disponibilidad?",
            tokens_used=12,
            created_at=created,
        )
        conv = _make_conversation(
            id=cid,
            wa_phone_number="573001234567",
            status="active",
        )
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.find_by_id.return_value = conv
        mock_repo.get_messages.return_value = [msg]

        uc = GetConversationMessagesUseCase(mock_repo)
        inp = GetConversationMessagesInput(conversation_id=self.CONVERSATION_ID)

        msg_outputs, _, _ = await uc.execute(inp)

        m = msg_outputs[0]
        assert m.id == str(mid)
        assert m.conversation_id == self.CONVERSATION_ID
        assert m.role == "user"
        assert m.content == "Hola, ¿tienen disponibilidad?"
        assert m.tokens_used == 12
        assert m.created_at == "2026-06-10T14:30:00+00:00"


# ============================================================================
# GetConversationStatsUseCase
# ============================================================================


class TestGetConversationStatsUseCase:
    """Happy path: returns counts, zero counts when no data exists."""

    @pytest.mark.asyncio
    async def test_returns_counts(self) -> None:
        """Valid stats from repo → ConversationStatsOutput with all fields."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.get_stats.return_value = {
            "total_conversations": 150,
            "active_conversations": 42,
            "messages_today": 87,
            "clients_with_conversations": 12,
        }

        uc = GetConversationStatsUseCase(mock_repo)
        output = await uc.execute()

        assert isinstance(output, ConversationStatsOutput)
        assert output.total_conversations == 150
        assert output.active_conversations == 42
        assert output.messages_today == 87
        assert output.clients_with_conversations == 12
        mock_repo.get_stats.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_zero_counts_when_empty(self) -> None:
        """No conversations at all → all stats are zero."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.get_stats.return_value = {
            "total_conversations": 0,
            "active_conversations": 0,
            "messages_today": 0,
            "clients_with_conversations": 0,
        }

        uc = GetConversationStatsUseCase(mock_repo)
        output = await uc.execute()

        assert output.total_conversations == 0
        assert output.active_conversations == 0
        assert output.messages_today == 0
        assert output.clients_with_conversations == 0

    @pytest.mark.asyncio
    async def test_no_input_required(self) -> None:
        """Stats use case takes no input — execute() with no arguments."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.get_stats.return_value = {
            "total_conversations": 1,
            "active_conversations": 1,
            "messages_today": 0,
            "clients_with_conversations": 1,
        }

        uc = GetConversationStatsUseCase(mock_repo)
        output = await uc.execute()

        assert output.total_conversations == 1

    @pytest.mark.asyncio
    async def test_all_counts_are_integers(self) -> None:
        """All fields in ConversationStatsOutput are ints, never None."""
        mock_repo = AsyncMock(spec=ConversationRepository)
        mock_repo.get_stats.return_value = {
            "total_conversations": 5,
            "active_conversations": 3,
            "messages_today": 12,
            "clients_with_conversations": 2,
        }

        uc = GetConversationStatsUseCase(mock_repo)
        output = await uc.execute()

        assert isinstance(output.total_conversations, int)
        assert isinstance(output.active_conversations, int)
        assert isinstance(output.messages_today, int)
        assert isinstance(output.clients_with_conversations, int)
