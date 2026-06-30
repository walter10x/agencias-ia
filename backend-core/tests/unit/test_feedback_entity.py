"""Tests for Feedback domain entity (RED phase — TDD).

These tests import entity classes that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: Feedback creation/validation, rating validation (1-5),
optional fields (lead_id, conversation_id), equality/hash.
"""

from __future__ import annotations

from uuid import UUID

import pytest

# --- Domain entity (does NOT exist yet — RED phase) ---
from app.domain.feedback.entity import Feedback


# ============================================================================
# Feedback entity — creation & validation
# ============================================================================


class TestFeedbackCreation:
    """Happy path: Feedback created with minimum valid data."""

    def test_creates_with_minimum_data(self) -> None:
        fb = Feedback(rating=5)

        assert fb.id is not None
        assert isinstance(fb.id, UUID)

        assert fb.client_id is not None
        assert isinstance(fb.client_id, UUID)

        assert fb.rating == 5
        assert fb.comment == ""
        assert fb.lead_id is None
        assert fb.conversation_id is None
        assert fb.created_at is not None

    def test_sets_default_values(self) -> None:
        """Defaults: rating=5, comment='', lead_id=None, conversation_id=None."""
        fb = Feedback()
        assert fb.rating == 5
        assert fb.comment == ""
        assert fb.lead_id is None
        assert fb.conversation_id is None

    def test_accepts_all_fields(self) -> None:
        """All fields explicitly set at construction."""
        fid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        cid = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        lid = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        convid = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

        fb = Feedback(
            id=fid,
            client_id=cid,
            lead_id=lid,
            conversation_id=convid,
            rating=4,
            comment="Buen servicio, rápido y eficiente",
        )

        assert fb.id == fid
        assert fb.client_id == cid
        assert fb.lead_id == lid
        assert fb.conversation_id == convid
        assert fb.rating == 4
        assert fb.comment == "Buen servicio, rápido y eficiente"


# ============================================================================
# Feedback entity — rating validation
# ============================================================================


class TestFeedbackRatingValidation:
    """Rating must be between 1 and 5 inclusive."""

    def test_accepts_rating_1(self) -> None:
        fb = Feedback(rating=1)
        assert fb.rating == 1

    def test_accepts_rating_3(self) -> None:
        fb = Feedback(rating=3)
        assert fb.rating == 3

    def test_accepts_rating_5(self) -> None:
        fb = Feedback(rating=5)
        assert fb.rating == 5

    def test_raises_on_rating_0(self) -> None:
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Feedback(rating=0)

    def test_raises_on_rating_6(self) -> None:
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Feedback(rating=6)

    def test_raises_on_negative_rating(self) -> None:
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Feedback(rating=-1)

    def test_raises_on_rating_out_of_range_message_contains_value(self) -> None:
        """Error message includes the offending value."""
        with pytest.raises(ValueError, match="got 0"):
            Feedback(rating=0)
        with pytest.raises(ValueError, match="got 6"):
            Feedback(rating=6)


# ============================================================================
# Feedback entity — optional fields
# ============================================================================


class TestFeedbackOptionalFields:
    """lead_id and conversation_id are nullable (SET NULL on delete)."""

    def test_lead_id_defaults_to_none(self) -> None:
        fb = Feedback(rating=4)
        assert fb.lead_id is None

    def test_conversation_id_defaults_to_none(self) -> None:
        fb = Feedback(rating=4)
        assert fb.conversation_id is None

    def test_accepts_lead_id_as_uuid(self) -> None:
        lid = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        fb = Feedback(rating=5, lead_id=lid)
        assert fb.lead_id == lid

    def test_accepts_conversation_id_as_uuid(self) -> None:
        convid = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        fb = Feedback(rating=5, conversation_id=convid)
        assert fb.conversation_id == convid

    def test_accepts_both_optional_ids(self) -> None:
        lid = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        convid = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        fb = Feedback(rating=3, lead_id=lid, conversation_id=convid)
        assert fb.lead_id == lid
        assert fb.conversation_id == convid

    def test_allows_feedback_without_lead(self) -> None:
        """EC-28: Feedback sin lead asociado se crea igual."""
        fb = Feedback(rating=5, comment="Feedback general sin lead")
        assert fb.lead_id is None
        assert fb.comment == "Feedback general sin lead"


# ============================================================================
# Feedback entity — comment
# ============================================================================


class TestFeedbackComment:
    """Comment is optional and defaults to empty string."""

    def test_comment_defaults_to_empty(self) -> None:
        fb = Feedback(rating=5)
        assert fb.comment == ""

    def test_accepts_comment(self) -> None:
        fb = Feedback(rating=5, comment="Excelente atención")
        assert fb.comment == "Excelente atención"

    def test_accepts_empty_comment(self) -> None:
        fb = Feedback(rating=5, comment="")
        assert fb.comment == ""


# ============================================================================
# Feedback entity — equality and hash
# ============================================================================


class TestFeedbackEquality:
    """Feedback equality is based on id alone."""

    def test_same_id_are_equal(self) -> None:
        fid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        a = Feedback(id=fid, rating=5)
        b = Feedback(id=fid, rating=1)
        assert a == b

    def test_different_id_not_equal(self) -> None:
        a = Feedback(rating=5)
        b = Feedback(rating=5)
        assert a != b

    def test_not_equal_to_non_feedback(self) -> None:
        fb = Feedback(rating=5)
        assert fb != "not-a-feedback"
        assert fb != 42
        assert fb is not None

    def test_hash_is_stable(self) -> None:
        fid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        fb = Feedback(id=fid, rating=5)
        assert hash(fb) == hash(fid)
