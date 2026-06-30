"""Unit tests for Feedback application use cases (RED phase — TDD).

These tests import use case classes, DTOs, and errors that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: CreateFeedbackUseCase, ListFeedbackUseCase, GetFeedbackStatsUseCase.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.dtos import (
    CreateFeedbackInput,
    FeedbackOutput,
    FeedbackStatsOutput,
    GetFeedbackStatsInput,
    ListFeedbackInput,
)
from app.application.feedback.create_feedback import CreateFeedbackUseCase
from app.application.feedback.get_feedback_stats import GetFeedbackStatsUseCase
from app.application.feedback.list_feedback import ListFeedbackUseCase

# --- Domain layer (partially exists) ---
from app.domain.feedback.entity import Feedback
from app.domain.feedback.repository import FeedbackRepository
from app.domain.shared.errors import InvalidFeedbackError


# ============================================================================
# Helpers
# ============================================================================

TODAY = datetime(2026, 6, 11, tzinfo=timezone.utc)


def _make_feedback(**overrides: object) -> Feedback:
    """Factory for Feedback entities with overridable fields.

    Creates a valid Feedback and then applies overrides for testing convenience.
    """
    fb = Feedback(
        rating=int(overrides.get("rating", 5)),
        comment=str(overrides.get("comment", "")),
    )
    if "id" in overrides:
        object.__setattr__(fb, "id", overrides["id"])
    if "client_id" in overrides:
        object.__setattr__(fb, "client_id", overrides["client_id"])
    if "lead_id" in overrides:
        val = overrides["lead_id"]
        if val is not None:
            fb.lead_id = UUID(val) if isinstance(val, str) else val
        else:
            fb.lead_id = None
    if "conversation_id" in overrides:
        val = overrides["conversation_id"]
        if val is not None:
            fb.conversation_id = UUID(val) if isinstance(val, str) else val
        else:
            fb.conversation_id = None
    if "created_at" in overrides:
        object.__setattr__(fb, "created_at", overrides["created_at"])
    else:
        object.__setattr__(fb, "created_at", TODAY)
    return fb


# ============================================================================
# CreateFeedbackUseCase  (E6)
# ============================================================================


class TestCreateFeedbackUseCase:
    """CreateFeedbackUseCase: happy path, validation errors."""

    @pytest.mark.asyncio
    async def test_creates_feedback_successfully(self) -> None:
        """Valid input → FeedbackOutput, save called."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            rating=5,
            lead_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            conversation_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            comment="Excelente servicio, muy rápido",
        )

        output = await uc.execute(inp)

        # Repository calls
        mock_repo.save.assert_awaited_once()

        # Output shape
        assert isinstance(output, FeedbackOutput)
        assert output.rating == 5
        assert output.comment == "Excelente servicio, muy rápido"
        assert output.lead_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert output.conversation_id == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        assert output.client_id == "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_creates_feedback_without_lead(self) -> None:
        """EC-28: lead_id and conversation_id are optional."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            rating=3,
        )

        output = await uc.execute(inp)

        assert output.lead_id is None
        assert output.conversation_id is None
        assert output.rating == 3
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_feedback_with_comment_only(self) -> None:
        """Only rating and comment → success."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            rating=4,
            comment="Buen servicio",
        )

        output = await uc.execute(inp)

        assert output.rating == 4
        assert output.comment == "Buen servicio"
        assert output.lead_id is None
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_on_empty_client_id(self) -> None:
        """EC-21: empty client_id → InvalidFeedbackError, save not called."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="",
            rating=5,
        )

        with pytest.raises(InvalidFeedbackError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_whitespace_client_id(self) -> None:
        """Whitespace-only client_id → InvalidFeedbackError."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="   ",
            rating=5,
        )

        with pytest.raises(InvalidFeedbackError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_rating_0(self) -> None:
        """EC-20: rating 0 → InvalidFeedbackError."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            rating=0,
        )

        with pytest.raises(InvalidFeedbackError, match="Rating must be between 1 and 5"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_rating_6(self) -> None:
        """EC-20: rating 6 → InvalidFeedbackError."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            rating=6,
        )

        with pytest.raises(InvalidFeedbackError, match="Rating must be between 1 and 5"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_negative_rating(self) -> None:
        """Negative rating → InvalidFeedbackError."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = CreateFeedbackUseCase(repo=mock_repo)
        inp = CreateFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            rating=-1,
        )

        with pytest.raises(InvalidFeedbackError, match="Rating must be between 1 and 5"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()


# ============================================================================
# ListFeedbackUseCase  (E7)
# ============================================================================


class TestListFeedbackUseCase:
    """ListFeedbackUseCase: pagination, empty results."""

    @pytest.mark.asyncio
    async def test_lists_feedback_with_pagination(self) -> None:
        """Happy path: returns list[FeedbackOutput] + total count."""
        feedbacks = [
            _make_feedback(
                rating=5,
                comment=f"Feedback {i}",
                created_at=TODAY,
            )
            for i in range(3)
        ]
        mock_repo = AsyncMock(spec=FeedbackRepository)
        mock_repo.list_by_client.return_value = feedbacks
        mock_repo.count_by_client.return_value = 3

        uc = ListFeedbackUseCase(repo=mock_repo)
        inp = ListFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            limit=10,
            offset=0,
        )

        outputs, total = await uc.execute(inp)

        assert len(outputs) == 3
        assert total == 3
        assert all(isinstance(o, FeedbackOutput) for o in outputs)

        mock_repo.list_by_client.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
            limit=10,
            offset=0,
        )
        mock_repo.count_by_client.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
        )

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_feedback(self) -> None:
        """Client has no feedback → ([], 0)."""
        mock_repo = AsyncMock(spec=FeedbackRepository)
        mock_repo.list_by_client.return_value = []
        mock_repo.count_by_client.return_value = 0

        uc = ListFeedbackUseCase(repo=mock_repo)
        inp = ListFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
        )

        outputs, total = await uc.execute(inp)

        assert outputs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_raises_on_empty_client_id(self) -> None:
        """Missing client_id → ValueError."""
        mock_repo = AsyncMock(spec=FeedbackRepository)

        uc = ListFeedbackUseCase(repo=mock_repo)
        inp = ListFeedbackInput(client_id="")

        with pytest.raises(ValueError, match="client_id is required"):
            await uc.execute(inp)

        mock_repo.list_by_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_respects_limit_and_offset(self) -> None:
        """Pagination parameters are passed through to repository."""
        feedbacks = [_make_feedback(rating=5)]
        mock_repo = AsyncMock(spec=FeedbackRepository)
        mock_repo.list_by_client.return_value = feedbacks
        mock_repo.count_by_client.return_value = 1

        uc = ListFeedbackUseCase(repo=mock_repo)
        inp = ListFeedbackInput(
            client_id="11111111-1111-1111-1111-111111111111",
            limit=5,
            offset=10,
        )

        outputs, total = await uc.execute(inp)

        assert len(outputs) == 1
        mock_repo.list_by_client.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
            limit=5,
            offset=10,
        )


# ============================================================================
# GetFeedbackStatsUseCase  (E8)
# ============================================================================


class TestGetFeedbackStatsUseCase:
    """GetFeedbackStatsUseCase: returns aggregated feedback stats."""

    @pytest.mark.asyncio
    async def test_returns_stats_successfully(self) -> None:
        """Happy path: returns FeedbackStatsOutput with aggregated data."""
        mock_repo = AsyncMock(spec=FeedbackRepository)
        mock_repo.get_stats.return_value = {
            "total": 20,
            "average_rating": 4.35,
            "rating_distribution": {1: 1, 2: 2, 3: 3, 4: 5, 5: 9},
        }

        uc = GetFeedbackStatsUseCase(repo=mock_repo)
        inp = GetFeedbackStatsInput(
            client_id="11111111-1111-1111-1111-111111111111",
        )

        output = await uc.execute(inp)

        assert isinstance(output, FeedbackStatsOutput)
        assert output.total == 20
        assert output.average_rating == 4.35
        assert output.rating_distribution[1] == 1
        assert output.rating_distribution[5] == 9

        mock_repo.get_stats.assert_awaited_once_with(
            client_id="11111111-1111-1111-1111-111111111111",
        )

    @pytest.mark.asyncio
    async def test_returns_zero_stats_when_no_feedback(self) -> None:
        """Client with no feedback → zeroed stats."""
        mock_repo = AsyncMock(spec=FeedbackRepository)
        mock_repo.get_stats.return_value = {
            "total": 0,
            "average_rating": 0.0,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        }

        uc = GetFeedbackStatsUseCase(repo=mock_repo)
        inp = GetFeedbackStatsInput(
            client_id="11111111-1111-1111-1111-111111111111",
        )

        output = await uc.execute(inp)

        assert output.total == 0
        assert output.average_rating == 0.0
        assert all(output.rating_distribution[r] == 0 for r in range(1, 6))

    @pytest.mark.asyncio
    async def test_rating_distribution_has_all_keys(self) -> None:
        """Distribution includes keys 1 through 5, even if zero."""
        mock_repo = AsyncMock(spec=FeedbackRepository)
        mock_repo.get_stats.return_value = {
            "total": 0,
            "average_rating": 0.0,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        }

        uc = GetFeedbackStatsUseCase(repo=mock_repo)
        inp = GetFeedbackStatsInput(
            client_id="11111111-1111-1111-1111-111111111111",
        )

        output = await uc.execute(inp)

        assert set(output.rating_distribution.keys()) == {1, 2, 3, 4, 5}
