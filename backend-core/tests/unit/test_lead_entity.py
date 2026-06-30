"""Tests for Lead domain entity and LeadStatus enum (RED phase — TDD).

These tests import entity classes that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: Lead creation/validation, LeadStatus enum, status transitions,
score boundaries, source validation, equality/hash.
"""

from __future__ import annotations

from uuid import UUID

import pytest

# --- Domain entities (do NOT exist yet — RED phase) ---
from app.domain.lead.entity import Lead, LeadStatus


# ============================================================================
# LeadStatus enum
# ============================================================================


class TestLeadStatusEnum:
    """LeadStatus enum values must match database CHECK constraint."""

    def test_enum_has_expected_values(self) -> None:
        assert LeadStatus.NEW.value == "new"
        assert LeadStatus.CONTACTED.value == "contacted"
        assert LeadStatus.INTERESTED.value == "interested"
        assert LeadStatus.NOT_INTERESTED.value == "not_interested"
        assert LeadStatus.CONVERTED.value == "converted"
        assert LeadStatus.ARCHIVED.value == "archived"

    def test_enum_values_are_strings(self) -> None:
        for status in LeadStatus:
            assert isinstance(status.value, str)

    def test_enum_members_are_unique(self) -> None:
        values = [m.value for m in LeadStatus]
        assert len(values) == len(set(values))

    def test_valid_statuses_classmethod(self) -> None:
        valid = LeadStatus.valid_statuses()
        assert "new" in valid
        assert "converted" in valid
        assert "archived" in valid
        assert len(valid) == 6

    def test_from_string_valid(self) -> None:
        assert LeadStatus("new") == LeadStatus.NEW
        assert LeadStatus("contacted") == LeadStatus.CONTACTED
        assert LeadStatus("interested") == LeadStatus.INTERESTED
        assert LeadStatus("not_interested") == LeadStatus.NOT_INTERESTED
        assert LeadStatus("converted") == LeadStatus.CONVERTED
        assert LeadStatus("archived") == LeadStatus.ARCHIVED

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            LeadStatus("deleted")
        with pytest.raises(ValueError):
            LeadStatus("unknown")


# ============================================================================
# Lead entity — creation & validation
# ============================================================================


class TestLeadCreation:
    """Happy path: Lead created with minimum valid data."""

    def test_creates_with_minimum_data(self) -> None:
        lead = Lead(phone="573001234567")

        assert lead.id is not None
        assert isinstance(lead.id, UUID)

        assert lead.client_id is not None
        assert isinstance(lead.client_id, UUID)

        assert lead.phone == "573001234567"
        assert lead.name == ""
        assert lead.status == LeadStatus.NEW
        assert lead.source == "whatsapp"
        assert lead.score == 0
        assert lead.notes == ""
        assert lead.last_contacted_at is None
        assert lead.created_at is not None
        assert lead.updated_at is not None

    def test_sets_default_values(self) -> None:
        """Defaults: status=new, source=whatsapp, score=0, notes=''."""
        lead = Lead(phone="573001234567")
        assert lead.status == LeadStatus.NEW
        assert lead.source == "whatsapp"
        assert lead.score == 0
        assert lead.notes == ""

    def test_accepts_all_fields(self) -> None:
        """All fields explicitly set at construction."""
        lid = UUID("11111111-1111-1111-1111-111111111111")
        cid = UUID("22222222-2222-2222-2222-222222222222")

        lead = Lead(
            id=lid,
            client_id=cid,
            phone="573009876543",
            name="Juan Pérez",
            status=LeadStatus.INTERESTED,
            source="webchat",
            score=50,
            notes="Cliente interesado en paquete premium",
        )

        assert lead.id == lid
        assert lead.client_id == cid
        assert lead.phone == "573009876543"
        assert lead.name == "Juan Pérez"
        assert lead.status == LeadStatus.INTERESTED
        assert lead.source == "webchat"
        assert lead.score == 50
        assert lead.notes == "Cliente interesado en paquete premium"

    def test_raises_on_empty_phone(self) -> None:
        with pytest.raises(ValueError, match="phone cannot be empty"):
            Lead(phone="")

    def test_raises_on_whitespace_only_phone(self) -> None:
        with pytest.raises(ValueError, match="phone cannot be empty"):
            Lead(phone="   ")

    def test_raises_on_invalid_status_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            Lead(phone="573001234567", status="deleted")  # type: ignore[arg-type]

    def test_accepts_status_strings(self) -> None:
        """Status can be passed as raw string for adapter convenience."""
        for status in ("new", "contacted", "interested", "not_interested", "converted", "archived"):
            lead = Lead(phone="573001234567", status=status)  # type: ignore[arg-type]
            assert lead.status.value == status

    def test_raises_on_score_below_zero(self) -> None:
        with pytest.raises(ValueError, match="Score must be between 0 and 100"):
            Lead(phone="573001234567", score=-1)

    def test_raises_on_score_above_100(self) -> None:
        with pytest.raises(ValueError, match="Score must be between 0 and 100"):
            Lead(phone="573001234567", score=101)

    def test_accepts_score_boundaries(self) -> None:
        lead_0 = Lead(phone="573001234567", score=0)
        assert lead_0.score == 0

        lead_100 = Lead(phone="573001234567", score=100)
        assert lead_100.score == 100

    def test_raises_on_invalid_source(self) -> None:
        with pytest.raises(ValueError, match="Invalid source"):
            Lead(phone="573001234567", source="email")

    def test_accepts_valid_sources(self) -> None:
        for source in ("whatsapp", "webchat", "telegram", "manual", "import"):
            lead = Lead(phone="573001234567", source=source)
            assert lead.source == source

    def test_accepts_valid_sources_in_variable(self) -> None:
        """VALID_SOURCES frozenset is exposed on the class."""
        assert hasattr(Lead, "VALID_SOURCES")
        assert "whatsapp" in Lead.VALID_SOURCES
        assert "import" in Lead.VALID_SOURCES
        assert "email" not in Lead.VALID_SOURCES


# ============================================================================
# Lead entity — status transitions
# ============================================================================


class TestLeadStatusTransitions:
    """State machine: new → contacted → interested → converted, etc."""

    def test_mark_contacted_changes_status_and_timestamp(self) -> None:
        lead = Lead(phone="573001234567", status=LeadStatus.NEW)
        assert lead.last_contacted_at is None

        lead.mark_contacted()

        assert lead.status == LeadStatus.CONTACTED
        assert lead.last_contacted_at is not None

    def test_mark_interested_changes_status(self) -> None:
        lead = Lead(phone="573001234567", status=LeadStatus.CONTACTED)

        lead.mark_interested()

        assert lead.status == LeadStatus.INTERESTED
        assert lead.last_contacted_at is not None

    def test_mark_not_interested_resets_score_to_zero(self) -> None:
        lead = Lead(phone="573001234567", score=70)

        lead.mark_not_interested()

        assert lead.status == LeadStatus.NOT_INTERESTED
        assert lead.score == 0

    def test_mark_converted_sets_score_to_100(self) -> None:
        lead = Lead(phone="573001234567", score=60)

        lead.mark_converted()

        assert lead.status == LeadStatus.CONVERTED
        assert lead.score == 100

    def test_archive_changes_status(self) -> None:
        lead = Lead(phone="573001234567", status=LeadStatus.NOT_INTERESTED)

        lead.archive()

        assert lead.status == LeadStatus.ARCHIVED

    def test_full_pipeline_transition(self) -> None:
        """Simulate a complete lead journey: new → contacted → interested → converted."""
        lead = Lead(phone="573001234567")

        assert lead.status == LeadStatus.NEW

        lead.mark_contacted()
        assert lead.status == LeadStatus.CONTACTED
        assert lead.last_contacted_at is not None

        lead.mark_interested()
        assert lead.status == LeadStatus.INTERESTED

        lead.mark_converted()
        assert lead.status == LeadStatus.CONVERTED
        assert lead.score == 100

    def test_updated_at_advances_on_transition(self) -> None:
        lead = Lead(phone="573001234567")
        original_updated = lead.updated_at

        lead.mark_contacted()
        assert lead.updated_at >= original_updated


# ============================================================================
# Lead entity — score management
# ============================================================================


class TestLeadScore:
    """Score logic: add_score caps at 100, mark methods set specific values."""

    def test_add_score_increments(self) -> None:
        lead = Lead(phone="573001234567", score=10)
        lead.add_score(20)
        assert lead.score == 30

    def test_add_score_caps_at_100(self) -> None:
        lead = Lead(phone="573001234567", score=90)
        lead.add_score(20)
        assert lead.score == 100  # capped, not 110

    def test_add_score_does_not_exceed_100_from_exact(self) -> None:
        lead = Lead(phone="573001234567", score=100)
        lead.add_score(5)
        assert lead.score == 100

    def test_add_score_zero_is_noop(self) -> None:
        lead = Lead(phone="573001234567", score=50)
        lead.add_score(0)
        assert lead.score == 50

    def test_add_score_negative_decreases(self) -> None:
        lead = Lead(phone="573001234567", score=50)
        lead.add_score(-10)
        assert lead.score == 40  # min(100, 50 + (-10)) = 40

    def test_mark_not_interested_resets_to_zero_regardless(self) -> None:
        lead = Lead(phone="573001234567", score=80)
        lead.mark_not_interested()
        assert lead.score == 0

    def test_mark_converted_sets_to_100_regardless(self) -> None:
        lead = Lead(phone="573001234567", score=30)
        lead.mark_converted()
        assert lead.score == 100

    def test_updated_at_advances_on_score_change(self) -> None:
        lead = Lead(phone="573001234567", score=10)
        original_updated = lead.updated_at

        lead.add_score(20)
        assert lead.updated_at >= original_updated


# ============================================================================
# Lead entity — notes management
# ============================================================================


class TestLeadNotes:
    """Notes update logic."""

    def test_update_notes_changes_value(self) -> None:
        lead = Lead(phone="573001234567", notes="Initial notes")
        lead.update_notes("Updated notes")
        assert lead.notes == "Updated notes"

    def test_update_notes_empty_string(self) -> None:
        lead = Lead(phone="573001234567", notes="Old notes")
        lead.update_notes("")
        assert lead.notes == ""

    def test_updated_at_advances_on_notes_change(self) -> None:
        lead = Lead(phone="573001234567")
        original_updated = lead.updated_at

        lead.update_notes("New note")
        assert lead.updated_at >= original_updated


# ============================================================================
# Lead entity — equality and hash
# ============================================================================


class TestLeadEquality:
    """Lead equality is based on id alone."""

    def test_same_id_are_equal(self) -> None:
        lid = UUID("11111111-1111-1111-1111-111111111111")
        a = Lead(id=lid, phone="573001234567")
        b = Lead(id=lid, phone="573009876543")
        assert a == b

    def test_different_id_not_equal(self) -> None:
        a = Lead(phone="573001234567")
        b = Lead(phone="573001234567")
        assert a != b

    def test_not_equal_to_non_lead(self) -> None:
        lead = Lead(phone="573001234567")
        assert lead != "not-a-lead"
        assert lead != 42
        assert lead is not None

    def test_hash_is_stable(self) -> None:
        lid = UUID("11111111-1111-1111-1111-111111111111")
        lead = Lead(id=lid, phone="573001234567")
        assert hash(lead) == hash(lid)

    def test_equality_across_different_attributes(self) -> None:
        """Same id but different attrs — still equal (id is the identity)."""
        lid = UUID("11111111-1111-1111-1111-111111111111")
        a = Lead(id=lid, phone="573001234567", name="Alice")
        b = Lead(id=lid, phone="573001234567", name="Bob")
        assert a == b
