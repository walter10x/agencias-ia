"""Unit tests for Lead application use cases (RED phase — TDD).

These tests import use case classes, DTOs, and errors that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: CreateLeadUseCase, ListLeadsUseCase, UpdateLeadUseCase,
GetLeadStatsUseCase, SendProactiveMessageUseCase.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.dtos import (
    CreateLeadInput,
    GetLeadStatsInput,
    LeadOutput,
    LeadStatsOutput,
    ListLeadsInput,
    SendProactiveMessageInput,
    UpdateLeadInput,
)
from app.application.lead.create_lead import CreateLeadUseCase
from app.application.lead.get_lead_stats import GetLeadStatsUseCase
from app.application.lead.list_leads import ListLeadsUseCase
from app.application.lead.send_message import SendProactiveMessageUseCase
from app.application.lead.update_lead import UpdateLeadUseCase

# --- Domain layer (partially exists) ---
from app.domain.channels.message_sender_port import MessageSenderPort
from app.domain.lead.entity import Lead, LeadStatus
from app.domain.lead.repository import LeadRepository
from app.domain.shared.errors import (
    InvalidLeadError,
    LeadNotFoundError,
    ProactiveMessageLimitError,
)


# ============================================================================
# Helpers
# ============================================================================

TODAY = datetime(2026, 6, 11, tzinfo=timezone.utc)


def _make_lead(**overrides: object) -> Lead:
    """Factory for Lead entities with overridable fields.

    Creates a valid Lead and then applies overrides for testing convenience.
    """
    lead = Lead(
        phone=str(overrides.get("phone", "573001234567")),
        name=str(overrides.get("name", "Test Lead")),
        source=str(overrides.get("source", "whatsapp")),
    )
    if "id" in overrides:
        object.__setattr__(lead, "id", overrides["id"])
    if "client_id" in overrides:
        object.__setattr__(lead, "client_id", overrides["client_id"])
    if "status" in overrides:
        s = overrides["status"]
        if isinstance(s, LeadStatus):
            lead.status = s
        else:
            lead.status = LeadStatus(s)  # type: ignore[arg-type]
    if "score" in overrides:
        lead.score = int(overrides["score"])  # type: ignore[arg-type]
    if "notes" in overrides:
        lead.notes = str(overrides["notes"])
    if "created_at" in overrides:
        object.__setattr__(lead, "created_at", overrides["created_at"])
    else:
        object.__setattr__(lead, "created_at", TODAY)
    if "updated_at" in overrides:
        object.__setattr__(lead, "updated_at", overrides["updated_at"])
    else:
        object.__setattr__(lead, "updated_at", TODAY)
    return lead


# ============================================================================
# CreateLeadUseCase  (E1)
# ============================================================================


class TestCreateLeadUseCase:
    """CreateLeadUseCase: happy path, dedup (idempotent), validation errors."""

    @pytest.mark.asyncio
    async def test_creates_lead_successfully(self) -> None:
        """Valid input, no duplicate → LeadOutput, save called."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_client_and_phone.return_value = None

        uc = CreateLeadUseCase(repo=mock_repo)
        inp = CreateLeadInput(
            client_id="11111111-1111-1111-1111-111111111111",
            phone="573001234567",
            name="Juan Pérez",
            source="webchat",
        )

        output = await uc.execute(inp)

        # Repository calls
        mock_repo.find_by_client_and_phone.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
            phone="573001234567",
        )
        mock_repo.save.assert_awaited_once()

        # Output shape
        assert isinstance(output, LeadOutput)
        assert output.phone == "573001234567"
        assert output.name == "Juan Pérez"
        assert output.source == "webchat"
        assert output.status == "new"
        assert output.score == 0
        assert output.client_id == "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_returns_existing_lead_on_duplicate(self) -> None:
        """EC-04: same client_id + phone → returns existing lead (idempotent)."""
        existing_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        existing = _make_lead(
            id=existing_id,
            client_id=UUID("11111111-1111-1111-1111-111111111111"),
            phone="573001234567",
            name="Existing Lead",
        )
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_client_and_phone.return_value = existing

        uc = CreateLeadUseCase(repo=mock_repo)
        inp = CreateLeadInput(
            client_id="11111111-1111-1111-1111-111111111111",
            phone="573001234567",
            name="New Name",
        )

        output = await uc.execute(inp)

        # Should NOT have saved a new lead
        mock_repo.save.assert_not_awaited()
        # Should return the existing lead's data
        assert output.id == str(existing_id)
        assert output.name == "Existing Lead"

    @pytest.mark.asyncio
    async def test_raises_on_empty_client_id(self) -> None:
        """EC-01: empty client_id → InvalidLeadError, save not called."""
        mock_repo = AsyncMock(spec=LeadRepository)
        uc = CreateLeadUseCase(repo=mock_repo)

        inp = CreateLeadInput(
            client_id="",
            phone="573001234567",
        )

        with pytest.raises(InvalidLeadError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_whitespace_client_id(self) -> None:
        """Whitespace-only client_id → InvalidLeadError."""
        mock_repo = AsyncMock(spec=LeadRepository)
        uc = CreateLeadUseCase(repo=mock_repo)

        inp = CreateLeadInput(
            client_id="   ",
            phone="573001234567",
        )

        with pytest.raises(InvalidLeadError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_empty_phone(self) -> None:
        """EC-02: empty phone → InvalidLeadError, save not called."""
        mock_repo = AsyncMock(spec=LeadRepository)
        uc = CreateLeadUseCase(repo=mock_repo)

        inp = CreateLeadInput(
            client_id="11111111-1111-1111-1111-111111111111",
            phone="",
        )

        with pytest.raises(InvalidLeadError, match="phone is required"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_source(self) -> None:
        """EC-05: invalid source → InvalidLeadError from entity."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_client_and_phone.return_value = None

        uc = CreateLeadUseCase(repo=mock_repo)
        inp = CreateLeadInput(
            client_id="11111111-1111-1111-1111-111111111111",
            phone="573001234567",
            source="email",
        )

        with pytest.raises(InvalidLeadError, match="Invalid source"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()


# ============================================================================
# ListLeadsUseCase  (E2)
# ============================================================================


class TestListLeadsUseCase:
    """ListLeadsUseCase: pagination, status filter, empty results."""

    @pytest.mark.asyncio
    async def test_lists_leads_with_pagination(self) -> None:
        """Happy path: returns list[LeadOutput] + total count."""
        leads = [_make_lead(name=f"Lead {i}") for i in range(3)]
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.list_by_client.return_value = leads
        mock_repo.count_by_client.return_value = 3

        uc = ListLeadsUseCase(repo=mock_repo)
        inp = ListLeadsInput(
            client_id="11111111-1111-1111-1111-111111111111",
            limit=10,
            offset=0,
        )

        outputs, total = await uc.execute(inp)

        assert len(outputs) == 3
        assert total == 3
        assert all(isinstance(o, LeadOutput) for o in outputs)
        assert outputs[0].name == "Lead 0"
        assert outputs[2].name == "Lead 2"

        mock_repo.list_by_client.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
            status=None,
            limit=10,
            offset=0,
        )
        mock_repo.count_by_client.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
            status=None,
        )

    @pytest.mark.asyncio
    async def test_filters_by_status(self) -> None:
        """Filter by status='new' → only matching leads returned."""
        new_leads = [_make_lead(name="New Lead", status="new")]
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.list_by_client.return_value = new_leads
        mock_repo.count_by_client.return_value = 1

        uc = ListLeadsUseCase(repo=mock_repo)
        inp = ListLeadsInput(
            client_id="11111111-1111-1111-1111-111111111111",
            status="new",
        )

        outputs, total = await uc.execute(inp)

        assert len(outputs) == 1
        assert total == 1
        assert outputs[0].status == "new"

        mock_repo.list_by_client.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
            status="new",
            limit=20,
            offset=0,
        )

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_leads(self) -> None:
        """EC-09, EC-10: client has no leads → ([], 0)."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.list_by_client.return_value = []
        mock_repo.count_by_client.return_value = 0

        uc = ListLeadsUseCase(repo=mock_repo)
        inp = ListLeadsInput(
            client_id="11111111-1111-1111-1111-111111111111",
        )

        outputs, total = await uc.execute(inp)

        assert outputs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_raises_on_empty_client_id(self) -> None:
        """Missing client_id → ValueError."""
        mock_repo = AsyncMock(spec=LeadRepository)
        uc = ListLeadsUseCase(repo=mock_repo)

        inp = ListLeadsInput(client_id="")

        with pytest.raises(ValueError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.list_by_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_filter_by_status_no_matches(self) -> None:
        """EC-10: status filter with zero results → ([], 0)."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.list_by_client.return_value = []
        mock_repo.count_by_client.return_value = 0

        uc = ListLeadsUseCase(repo=mock_repo)
        inp = ListLeadsInput(
            client_id="11111111-1111-1111-1111-111111111111",
            status="converted",
        )

        outputs, total = await uc.execute(inp)

        assert outputs == []
        assert total == 0


# ============================================================================
# UpdateLeadUseCase  (E3)
# ============================================================================


class TestUpdateLeadUseCase:
    """UpdateLeadUseCase: update status, score, notes; validation errors."""

    LEAD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    LEAD_UUID = UUID(LEAD_ID)

    @pytest.mark.asyncio
    async def test_updates_status_successfully(self) -> None:
        """Update only status → LeadOutput with new status."""
        lead = _make_lead(id=self.LEAD_UUID, status=LeadStatus.NEW, score=40)
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(
            lead_id=self.LEAD_ID,
            status="interested",
        )

        output = await uc.execute(inp)

        assert output.status == "interested"
        assert output.score == 40  # unchanged
        mock_repo.find_by_id.assert_awaited_once_with(self.LEAD_ID)
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_score_successfully(self) -> None:
        """Update only score → LeadOutput with new score."""
        lead = _make_lead(id=self.LEAD_UUID, score=30)
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(
            lead_id=self.LEAD_ID,
            score=80,
        )

        output = await uc.execute(inp)

        assert output.score == 80

    @pytest.mark.asyncio
    async def test_updates_notes_successfully(self) -> None:
        """Update only notes → LeadOutput with new notes."""
        lead = _make_lead(id=self.LEAD_UUID, notes="Old notes")
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(
            lead_id=self.LEAD_ID,
            notes="Updated notes",
        )

        output = await uc.execute(inp)

        assert output.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_updates_name_successfully(self) -> None:
        """Update only name → LeadOutput with new name."""
        lead = _make_lead(id=self.LEAD_UUID, name="Old Name")
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(
            lead_id=self.LEAD_ID,
            name="New Name",
        )

        output = await uc.execute(inp)

        assert output.name == "New Name"

    @pytest.mark.asyncio
    async def test_updates_multiple_fields(self) -> None:
        """Update status + score + notes simultaneously."""
        lead = _make_lead(
            id=self.LEAD_UUID,
            status=LeadStatus.NEW,
            score=10,
            notes="Old",
        )
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(
            lead_id=self.LEAD_ID,
            status="interested",
            score=70,
            notes="Cliente interesado en servicios",
        )

        output = await uc.execute(inp)

        assert output.status == "interested"
        assert output.score == 70
        assert output.notes == "Cliente interesado en servicios"

    @pytest.mark.asyncio
    async def test_raises_on_invalid_uuid(self) -> None:
        """EC-11: non-UUID lead_id → LeadNotFoundError."""
        mock_repo = AsyncMock(spec=LeadRepository)
        uc = UpdateLeadUseCase(repo=mock_repo)

        inp = UpdateLeadInput(lead_id="not-a-uuid", status="interested")

        with pytest.raises(LeadNotFoundError, match="Invalid lead ID"):
            await uc.execute(inp)

        mock_repo.find_by_id.assert_not_awaited()
        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_lead_not_found(self) -> None:
        """EC-12: non-existent lead_id → LeadNotFoundError."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = None

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(lead_id=self.LEAD_ID, status="interested")

        with pytest.raises(LeadNotFoundError, match="Lead not found"):
            await uc.execute(inp)

        mock_repo.find_by_id.assert_awaited_once_with(self.LEAD_ID)
        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_status(self) -> None:
        """EC-14: invalid status value → InvalidLeadError."""
        lead = _make_lead(id=self.LEAD_UUID)
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(lead_id=self.LEAD_ID, status="deleted")

        with pytest.raises(InvalidLeadError, match="Invalid status"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_score_below_zero(self) -> None:
        """EC-13: score < 0 → InvalidLeadError."""
        lead = _make_lead(id=self.LEAD_UUID)
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(lead_id=self.LEAD_ID, score=-5)

        with pytest.raises(InvalidLeadError, match="Score must be between 0 and 100"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_score_above_100(self) -> None:
        """EC-13: score > 100 → InvalidLeadError."""
        lead = _make_lead(id=self.LEAD_UUID)
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(lead_id=self.LEAD_ID, score=150)

        with pytest.raises(InvalidLeadError, match="Score must be between 0 and 100"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_contacted_status_updates_last_contacted_at(self) -> None:
        """Setting status to 'contacted' updates last_contacted_at."""
        lead = _make_lead(id=self.LEAD_UUID, status=LeadStatus.NEW)
        assert lead.last_contacted_at is None

        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(lead_id=self.LEAD_ID, status="contacted")

        output = await uc.execute(inp)

        assert output.status == "contacted"
        # The entity should have been updated in memory
        assert lead.last_contacted_at is not None

    @pytest.mark.asyncio
    async def test_not_interested_resets_score(self) -> None:
        """Setting status to 'not_interested' resets score to 0."""
        lead = _make_lead(id=self.LEAD_UUID, score=80)
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        uc = UpdateLeadUseCase(repo=mock_repo)
        inp = UpdateLeadInput(lead_id=self.LEAD_ID, status="not_interested")

        output = await uc.execute(inp)

        assert output.status == "not_interested"
        assert output.score == 0


# ============================================================================
# GetLeadStatsUseCase  (E4)
# ============================================================================


class TestGetLeadStatsUseCase:
    """GetLeadStatsUseCase: returns aggregated stats from repository."""

    LEAD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    @pytest.mark.asyncio
    async def test_returns_stats_successfully(self) -> None:
        """Happy path: returns LeadStatsOutput with aggregated data."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.get_stats.return_value = {
            "total": 50,
            "by_status": {
                "new": 10,
                "contacted": 15,
                "interested": 12,
                "not_interested": 8,
                "converted": 3,
                "archived": 2,
            },
            "conversion_rate": 6.0,
            "new_today": 2,
            "avg_score": 45.5,
        }

        uc = GetLeadStatsUseCase(repo=mock_repo)
        inp = GetLeadStatsInput(
            client_id="11111111-1111-1111-1111-111111111111",
        )

        output = await uc.execute(inp)

        assert isinstance(output, LeadStatsOutput)
        assert output.total == 50
        assert output.by_status["new"] == 10
        assert output.by_status["converted"] == 3
        assert output.conversion_rate == 6.0
        assert output.new_today == 2
        assert output.avg_score == 45.5

        mock_repo.get_stats.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
        )

    @pytest.mark.asyncio
    async def test_returns_zero_stats_when_no_leads(self) -> None:
        """Client with no leads → all stats at zero."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.get_stats.return_value = {
            "total": 0,
            "by_status": {},
            "conversion_rate": 0.0,
            "new_today": 0,
            "avg_score": 0.0,
        }

        uc = GetLeadStatsUseCase(repo=mock_repo)
        inp = GetLeadStatsInput(
            client_id="11111111-1111-1111-1111-111111111111",
        )

        output = await uc.execute(inp)

        assert output.total == 0
        assert output.by_status == {}
        assert output.conversion_rate == 0.0
        assert output.new_today == 0
        assert output.avg_score == 0.0


# ============================================================================
# SendProactiveMessageUseCase  (E5)
# ============================================================================


class TestSendProactiveMessageUseCase:
    """SendProactiveMessageUseCase: send, rate limit, not found errors."""

    LEAD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    LEAD_UUID = UUID(LEAD_ID)

    @pytest.mark.asyncio
    async def test_sends_message_successfully(self) -> None:
        """Happy path: message sent, lead status updated to contacted."""
        lead = _make_lead(
            id=self.LEAD_UUID,
            phone="573001234567",
            status=LeadStatus.NEW,
        )
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        mock_sender = AsyncMock(spec=MessageSenderPort)
        mock_sender.count_sent_today.return_value = 42  # below 100 limit
        mock_sender.send.return_value = True

        uc = SendProactiveMessageUseCase(
            lead_repo=mock_repo,
            message_sender=mock_sender,
        )
        inp = SendProactiveMessageInput(
            lead_id=self.LEAD_ID,
            message_text="¡Hola! ¿Has pensado en nuestros servicios?",
        )

        await uc.execute(inp)

        # Rate limit checked
        mock_sender.count_sent_today.assert_awaited_once()
        # Message sent
        mock_sender.send.assert_awaited_once_with(
            phone="573001234567",
            text="¡Hola! ¿Has pensado en nuestros servicios?",
        )
        # Lead updated to contacted
        mock_repo.save.assert_awaited_once()
        assert lead.status == LeadStatus.CONTACTED

    @pytest.mark.asyncio
    async def test_raises_on_rate_limit_exceeded(self) -> None:
        """EC-16: daily limit (100) reached → ProactiveMessageLimitError."""
        lead = _make_lead(
            id=self.LEAD_UUID,
            phone="573001234567",
        )
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        mock_sender = AsyncMock(spec=MessageSenderPort)
        mock_sender.count_sent_today.return_value = 100  # already at limit

        uc = SendProactiveMessageUseCase(
            lead_repo=mock_repo,
            message_sender=mock_sender,
        )
        inp = SendProactiveMessageInput(
            lead_id=self.LEAD_ID,
            message_text="Hola",
        )

        with pytest.raises(
            ProactiveMessageLimitError,
            match="Daily proactive message limit",
        ):
            await uc.execute(inp)

        # Message should NOT be sent
        mock_sender.send.assert_not_awaited()
        # Lead should NOT be saved
        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_when_lead_not_found(self) -> None:
        """EC-17: non-existent lead → LeadNotFoundError."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = None

        mock_sender = AsyncMock(spec=MessageSenderPort)

        uc = SendProactiveMessageUseCase(
            lead_repo=mock_repo,
            message_sender=mock_sender,
        )
        inp = SendProactiveMessageInput(
            lead_id=self.LEAD_ID,
            message_text="Hola",
        )

        with pytest.raises(LeadNotFoundError, match="Lead not found"):
            await uc.execute(inp)

        mock_sender.count_sent_today.assert_not_awaited()
        mock_sender.send.assert_not_awaited()
        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_lead_uuid(self) -> None:
        """Non-UUID lead_id → LeadNotFoundError before any checks."""
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_sender = AsyncMock(spec=MessageSenderPort)

        uc = SendProactiveMessageUseCase(
            lead_repo=mock_repo,
            message_sender=mock_sender,
        )
        inp = SendProactiveMessageInput(
            lead_id="not-a-uuid",
            message_text="Hola",
        )

        with pytest.raises(LeadNotFoundError, match="Invalid lead ID"):
            await uc.execute(inp)

        mock_repo.find_by_id.assert_not_awaited()
        mock_sender.send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_daily_limit_is_100(self) -> None:
        """DAILY_LIMIT constant is 100."""
        assert SendProactiveMessageUseCase.DAILY_LIMIT == 100

    @pytest.mark.asyncio
    async def test_sends_message_at_exactly_99_sent_today(self) -> None:
        """At exactly 99 sent today, one more message is allowed."""
        lead = _make_lead(
            id=self.LEAD_UUID,
            phone="573001234567",
            status=LeadStatus.NEW,
        )
        mock_repo = AsyncMock(spec=LeadRepository)
        mock_repo.find_by_id.return_value = lead

        mock_sender = AsyncMock(spec=MessageSenderPort)
        mock_sender.count_sent_today.return_value = 99
        mock_sender.send.return_value = True

        uc = SendProactiveMessageUseCase(
            lead_repo=mock_repo,
            message_sender=mock_sender,
        )
        inp = SendProactiveMessageInput(
            lead_id=self.LEAD_ID,
            message_text="Test message",
        )

        await uc.execute(inp)

        mock_sender.send.assert_awaited_once()
        mock_repo.save.assert_awaited_once()
