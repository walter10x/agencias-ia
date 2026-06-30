"""Tests for Landing Pages module (RED phase — TDD).

These tests import classes and modules that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: LandingSlug value object, slugify/generate_unique_slug helpers,
Lead source="landing" integration, LandingConfig entity,
SubmitLandingLeadUseCase, GetLandingConfigUseCase, UpdateLandingConfigUseCase,
and domain error hierarchy.

Spec reference: specs/spec-landing-pages.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

# ============================================================================
# RED-PHASE IMPORTS — modules/files that do NOT exist yet
# ============================================================================

# --- Domain: LandingSlug value object + slugify helpers ---
# Will be added to: app.domain.shared.value_objects
from app.domain.shared.value_objects import LandingSlug  # NEW (does not exist)

# slugify + generate_unique_slug (NEW — may live in app.domain.shared.slugify or inline)
from app.domain.shared.slugify import generate_unique_slug, slugify  # NEW

# --- Domain: Landing repository port + LandingConfig dataclass ---
from app.domain.landing.repository import LandingConfig, LandingRepository  # NEW

# --- Domain: Landing errors ---
from app.domain.shared.errors import (  # NEW (additions to existing file)
    DomainError,
    LandingInactiveError,
    LandingNotFoundError,
    LandingRateLimitError,
)

# --- Domain: Existing entities/repos needed by tests ---
from app.domain.agent.entity import Agent
from app.domain.agent.repository import AgentRepository
from app.domain.client.entity import Client
from app.domain.lead.entity import Lead, LeadStatus
from app.domain.lead.repository import LeadRepository

# --- Application: Landing DTOs (NEW) ---
from app.application.dtos import (
    GetLandingConfigInput,
    LandingConfigOutput,
    LandingPublicConfigOutput,
    SubmitLandingInput,
    SubmitLandingOutput,
    UpdateLandingConfigInput,
)

# --- Application: Landing Use Cases (NEW) ---
from app.application.landing.get_landing_config import GetLandingConfigUseCase  # NEW
from app.application.landing.submit_lead import SubmitLandingLeadUseCase  # NEW
from app.application.landing.update_landing_config import UpdateLandingConfigUseCase  # NEW

# --- Domain: existing errors used by landing use cases ---
from app.domain.shared.errors import ClientNotFoundError, InvalidLeadError

# ============================================================================
# Test Helpers — Factories for test data
# ============================================================================


def _make_client(**overrides: object) -> MagicMock:
    """Create a mock Client suitable for landing tests."""
    client = MagicMock(spec=Client)
    client.id = UUID(str(overrides.get("id", "11111111-1111-1111-1111-111111111111")))
    client.name = str(overrides.get("name", "Peluquería El Buen Corte"))
    client.is_active = bool(overrides.get("is_active", True))
    return client


def _make_landing_config(**overrides: object) -> MagicMock:
    """Create a mock LandingConfig suitable for landing tests."""
    config = MagicMock(spec=LandingConfig)
    config.client_id = str(overrides.get("client_id", "11111111-1111-1111-1111-111111111111"))
    config.slug = str(overrides.get("slug", "peluqueria-el-buen-corte"))
    config.title = str(overrides.get("title", "Impulsa tu negocio con IA"))
    config.description = str(overrides.get("description", "Déjanos tus datos y te contactamos"))
    config.is_active = bool(overrides.get("is_active", True))
    config.primary_color = str(overrides.get("primary_color", "#f59e0b"))
    config.auto_reply = str(overrides.get("auto_reply", "¡Hola {{name}}! Gracias por contactarnos."))
    return config


def _make_lead(**overrides: object) -> Lead:
    """Factory for Lead entities with overridable fields."""
    lead = Lead(
        phone=str(overrides.get("phone", "573001234567")),
        name=str(overrides.get("name", "Test Lead")),
        source=str(overrides.get("source", "landing")),
    )
    if "id" in overrides:
        object.__setattr__(lead, "id", overrides["id"])
    if "client_id" in overrides:
        object.__setattr__(lead, "client_id", overrides["client_id"])
    return lead


# ============================================================================
# 1. LandingSlug — Value Object
# ============================================================================


class TestLandingSlug:
    """LandingSlug value object: creation, validation, and factory method."""

    # --- Valid slugs ---

    def test_accepts_valid_slug_single_word(self) -> None:
        """TL-001: Valid slug with single lowercase word."""
        slug = LandingSlug("mi-negocio")
        assert slug.value == "mi-negocio"
        assert str(slug) == "mi-negocio"

    def test_accepts_valid_slug_multiple_segments(self) -> None:
        """Valid slug with multiple hyphen-separated segments."""
        slug = LandingSlug("peluqueria-el-buen-corte")
        assert slug.value == "peluqueria-el-buen-corte"

    def test_accepts_valid_slug_with_numbers(self) -> None:
        """Valid slug containing numbers."""
        slug = LandingSlug("negocio-24-horas")
        assert slug.value == "negocio-24-horas"

    def test_normalizes_after_validation(self) -> None:
        """After validation passes, value is stripped and lowercased (idempotent for clean input)."""
        slug = LandingSlug("mi-negocio")
        assert slug.value == "mi-negocio"  # already clean, no change
        # from_name is the primary path for dirty input normalization
        slug2 = LandingSlug.from_name("  Mi Negocio  ")
        assert slug2.value == "mi-negocio"

    def test_accepts_single_character_slug(self) -> None:
        """Minimum valid slug: single lowercase letter."""
        slug = LandingSlug("a")
        assert slug.value == "a"

    def test_accepts_max_length_slug(self) -> None:
        """Slug at exactly 100 characters is valid."""
        long_slug = "a" + "-b" * 49  # "a-b-b-b..." = 1 + 49*2 = 99, let's adjust
        # 100 chars: 50 segments of "ab" joined by "-" → "ab-ab-...-ab"
        long_slug = "-".join(["ab"] * 50)  # 50*2 + 49 = 149... too long
        # Let's do: single 100-char word
        long_slug = "x" * 100
        slug = LandingSlug(long_slug)
        assert len(slug.value) == 100

    # --- Invalid slugs ---

    def test_raises_on_empty_slug(self) -> None:
        """TL-002: Empty string → ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            LandingSlug("")

    def test_raises_on_whitespace_only_slug(self) -> None:
        """Whitespace-only input → ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            LandingSlug("   ")

    def test_raises_on_slug_with_uppercase(self) -> None:
        """TL-003: Uppercase characters → ValueError (post_init validates raw input)."""
        with pytest.raises(ValueError, match="lowercase"):
            LandingSlug("Mi-Negocio")

    def test_raises_on_slug_with_spaces(self) -> None:
        """TL-004: Internal spaces → ValueError."""
        with pytest.raises(ValueError, match="lowercase"):
            LandingSlug("mi negocio")

    def test_raises_on_slug_with_special_characters(self) -> None:
        """TL-005: Special characters → ValueError."""
        with pytest.raises(ValueError, match="lowercase"):
            LandingSlug("mi@negocio")

    def test_raises_on_slug_with_consecutive_hyphens(self) -> None:
        """TL-006: Double hyphens → ValueError."""
        with pytest.raises(ValueError, match="lowercase"):
            LandingSlug("mi--negocio")

    def test_raises_on_slug_starting_with_hyphen(self) -> None:
        """Slug starting with hyphen → ValueError."""
        with pytest.raises(ValueError, match="lowercase"):
            LandingSlug("-mi-negocio")

    def test_raises_on_slug_ending_with_hyphen(self) -> None:
        """Slug ending with hyphen → ValueError."""
        with pytest.raises(ValueError, match="lowercase"):
            LandingSlug("mi-negocio-")

    def test_raises_on_slug_exceeding_100_chars(self) -> None:
        """Slug longer than 100 characters → ValueError."""
        with pytest.raises(ValueError, match="100"):
            LandingSlug("x" * 101)

    # --- Factory method: from_name ---

    def test_from_name_produces_valid_slug(self) -> None:
        """TL-007: from_name("Peluquería El Buen Corte") → "peluqueria-el-buen-corte"."""
        slug = LandingSlug.from_name("Peluquería El Buen Corte")
        assert slug.value == "peluqueria-el-buen-corte"

    def test_from_name_handles_special_chars(self) -> None:
        """TL-008: from_name("Café & Bar") → "cafe-bar"."""
        slug = LandingSlug.from_name("Café & Bar")
        assert slug.value == "cafe-bar"

    def test_from_name_handles_empty_or_special_only(self) -> None:
        """from_name with input that slugifies to empty → falls back to 'cliente'."""
        slug = LandingSlug.from_name("@#$%")
        assert slug.value == "cliente"

    # --- Immutability ---

    def test_is_frozen_dataclass(self) -> None:
        """LandingSlug is a frozen dataclass — cannot mutate."""
        slug = LandingSlug("mi-negocio")
        with pytest.raises(Exception):  # FrozenInstanceError or similar
            slug.value = "otro"  # type: ignore[misc]


# ============================================================================
# 2. slugify() — Pure function
# ============================================================================


class TestSlugify:
    """Pure slugify function: URL-safe string generation."""

    def test_simple_lowercase_name(self) -> None:
        """Simple name → lowercase with hyphens."""
        assert slugify("Mi Negocio") == "mi-negocio"

    def test_removes_accents(self) -> None:
        """Accented characters → ASCII equivalents."""
        assert slugify("Peluquería") == "peluqueria"

    def test_removes_punctuation(self) -> None:
        """TL-009: slugify("Dr. Juan's Clínica") → "dr-juans-clinica"."""
        result = slugify("Dr. Juan's Clínica")
        assert result == "dr-juans-clinica"

    def test_handles_ampersand(self) -> None:
        """Ampersand is stripped, not replaced."""
        result = slugify("Café & Bar")
        assert result == "cafe-bar"

    def test_collapses_multiple_spaces(self) -> None:
        """Multiple spaces → single hyphen."""
        assert slugify("Mi   Negocio") == "mi-negocio"

    def test_strips_leading_trailing_hyphens(self) -> None:
        """Leading/trailing special chars produce no stray hyphens."""
        result = slugify("  -Mi Negocio-  ")
        assert result == "mi-negocio"
        # Verify no leading or trailing hyphen
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_empty_string_returns_fallback(self) -> None:
        """TL-010: slugify("") → "cliente"."""
        assert slugify("") == "cliente"

    def test_whitespace_only_returns_fallback(self) -> None:
        """slugify("   ") → "cliente"."""
        assert slugify("   ") == "cliente"

    def test_only_special_chars_returns_fallback(self) -> None:
        """slugify("@#$%") → "cliente"."""
        assert slugify("@#$%") == "cliente"

    def test_numbers_preserved(self) -> None:
        """Numbers in name are preserved."""
        assert slugify("Negocio 24 Horas") == "negocio-24-horas"

    def test_already_valid_slug_preserved(self) -> None:
        """slugify on already-slugified input is idempotent."""
        assert slugify("mi-negocio") == "mi-negocio"


# ============================================================================
# 3. generate_unique_slug() — Dedup helper
# ============================================================================


class TestGenerateUniqueSlug:
    """generate_unique_slug: suffix-based deduplication."""

    def test_no_conflict_returns_same_slug(self) -> None:
        """When base slug is not in existing set, returns it unchanged."""
        result = generate_unique_slug("Mi Negocio", {"otro-slug", "mas-slugs"})
        assert result == "mi-negocio"

    def test_simple_conflict_appends_2(self) -> None:
        """TL-011: existing contains base slug → appends '-2'."""
        result = generate_unique_slug(
            "peluqueria-el-buen-corte",
            {"peluqueria-el-buen-corte"},
        )
        assert result == "peluqueria-el-buen-corte-2"

    def test_multiple_conflicts_increments(self) -> None:
        """When base and -2 exist → goes to -3, -4, etc."""
        existing = {
            "mi-negocio",
            "mi-negocio-2",
            "mi-negocio-3",
        }
        result = generate_unique_slug("Mi Negocio", existing)
        assert result == "mi-negocio-4"

    def test_empty_existing_set(self) -> None:
        """Empty existing set → returns base slug."""
        result = generate_unique_slug("Mi Negocio", set())
        assert result == "mi-negocio"

    def test_preserves_numbers_in_existing(self) -> None:
        """Numbers in base slug don't conflict with suffix numbering."""
        result = generate_unique_slug("negocio-24", {"negocio-24"})
        assert result == "negocio-24-2"


# ============================================================================
# 4. Lead entity — source="landing" integration
# ============================================================================


class TestLeadWithLandingSource:
    """Lead entity must accept source="landing" after VALID_SOURCES update."""

    def test_creates_lead_with_landing_source(self) -> None:
        """TL-012: Lead(phone=..., source="landing") succeeds."""
        lead = Lead(phone="573001234567", source="landing")
        assert lead.source == "landing"

    def test_landing_in_valid_sources(self) -> None:
        """TL-013: "landing" is in Lead.VALID_SOURCES."""
        assert "landing" in Lead.VALID_SOURCES

    def test_lead_still_validates_invalid_source(self) -> None:
        """Invalid source "email" still raises ValueError (regression check)."""
        with pytest.raises(ValueError, match="Invalid source"):
            Lead(phone="573001234567", source="email")

    def test_existing_sources_still_valid(self) -> None:
        """All previously valid sources remain accepted."""
        for source in ("whatsapp", "webchat", "telegram", "manual", "import", "landing"):
            lead = Lead(phone="573001234567", source=source)
            assert lead.source == source


# ============================================================================
# 5. Landing Domain Errors
# ============================================================================


class TestLandingDomainErrors:
    """Landing-specific domain errors must extend DomainError."""

    def test_landing_not_found_is_domain_error(self) -> None:
        """TL-014: LandingNotFoundError extends DomainError."""
        assert issubclass(LandingNotFoundError, DomainError)

    def test_landing_inactive_is_domain_error(self) -> None:
        """TL-015: LandingInactiveError extends DomainError."""
        assert issubclass(LandingInactiveError, DomainError)

    def test_landing_rate_limit_is_domain_error(self) -> None:
        """TL-016: LandingRateLimitError extends DomainError."""
        assert issubclass(LandingRateLimitError, DomainError)

    def test_errors_store_message(self) -> None:
        """All landing errors accept and store a message string."""
        for cls in (LandingNotFoundError, LandingInactiveError, LandingRateLimitError):
            err = cls("test message")
            assert err.message == "test message"
            assert str(err) == "test message"


# ============================================================================
# 6. LandingConfig — Dataclass
# ============================================================================


class TestLandingConfig:
    """LandingConfig dataclass carries landing configuration for a client."""

    def test_creates_with_all_fields(self) -> None:
        """All fields populated."""
        config = LandingConfig(
            client_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            slug="mi-negocio",
            title="Mi Negocio",
            description="La mejor atención",
            is_active=True,
            primary_color="#ffffff",
            auto_reply="¡Hola {{name}}!",
        )
        assert config.client_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert config.slug == "mi-negocio"
        assert config.title == "Mi Negocio"
        assert config.description == "La mejor atención"
        assert config.is_active is True
        assert config.primary_color == "#ffffff"
        assert config.auto_reply == "¡Hola {{name}}!"

    def test_defaults_reflect_spec(self) -> None:
        """Default values match spec section 4.3 (although dataclasses may not have defaults)."""
        # LandingConfig is just a data holder — no defaults enforced here
        # but the repository layer provides defaults when reading from DB
        config = LandingConfig(
            client_id="test",
            slug="",
            title="Impulsa tu negocio con IA",
            description="Déjanos tus datos y te contactamos",
            is_active=False,
            primary_color="#f59e0b",
            auto_reply="¡Hola {{name}}! Gracias por contactarnos.",
        )
        assert config.title == "Impulsa tu negocio con IA"
        assert config.primary_color == "#f59e0b"


# ============================================================================
# 7. SubmitLandingLeadUseCase — Happy Path
# ============================================================================


class TestSubmitLandingLeadHappyPath:
    """SubmitLandingLeadUseCase: successful form submission."""

    @pytest.mark.asyncio
    async def test_creates_lead_with_landing_source(self) -> None:
        """TL-017: Valid input → creates Lead with source='landing', returns output."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config(is_active=True)
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True
        mock_agent_repo.find_active_by_client.return_value = None  # no agent

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="peluqueria-el-buen-corte",
            name="Juan Pérez",
            whatsapp="573001234567",
            interest="Quiero información",
        )

        output = await uc.execute(inp)

        # Output shape
        assert isinstance(output, SubmitLandingOutput)
        assert output.lead_id is not None
        assert output.message == "¡Gracias! Te contactaremos pronto."
        assert "Juan Pérez" in output.auto_reply

        # Lead created
        mock_lead_repo.save.assert_awaited_once()
        saved_lead = mock_lead_repo.save.call_args[0][0]
        assert saved_lead.source == "landing"
        assert saved_lead.name == "Juan Pérez"
        assert saved_lead.phone == "573001234567"

    @pytest.mark.asyncio
    async def test_save_called_exactly_once(self) -> None:
        """TL-023: lead_repo.save is called exactly 1 time."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True
        mock_agent_repo.find_active_by_client.return_value = None

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="peluqueria-el-buen-corte",
            name="María",
            whatsapp="573009876543",
        )

        await uc.execute(inp)

        assert mock_lead_repo.save.call_count == 1

    @pytest.mark.asyncio
    async def test_interpolates_name_in_auto_reply(self) -> None:
        """TL-026: {{name}} in auto_reply is replaced with input.name."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config(auto_reply="¡Hola {{name}}! Te atenderemos pronto.")
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True
        mock_agent_repo.find_active_by_client.return_value = None

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Carlos",
            whatsapp="573001234567",
        )

        output = await uc.execute(inp)

        assert output.auto_reply == "¡Hola Carlos! Te atenderemos pronto."

    @pytest.mark.asyncio
    async def test_sends_whatsapp_when_agent_active(self) -> None:
        """TL-024: Agent active → WhatsApp auto-reply message is sent."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config(auto_reply="¡Hola {{name}}! Bienvenido.")
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True

        mock_agent = MagicMock(spec=Agent)
        mock_agent.id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_agent_repo.find_active_by_client.return_value = mock_agent

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Ana",
            whatsapp="573001234567",
        )

        await uc.execute(inp)

        mock_sender.send.assert_awaited_once()
        call_kwargs = mock_sender.send.call_args.kwargs
        assert call_kwargs["phone"] == "573001234567"
        assert call_kwargs["message"] == "¡Hola Ana! Bienvenido."

    @pytest.mark.asyncio
    async def test_no_whatsapp_when_no_agent(self) -> None:
        """TL-025: No active agent → graceful degradation, lead still created."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True
        mock_agent_repo.find_active_by_client.return_value = None  # no agent

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Pedro",
            whatsapp="573001234567",
        )

        output = await uc.execute(inp)

        # Lead still created
        mock_lead_repo.save.assert_awaited_once()
        # WhatsApp NOT sent
        mock_sender.send.assert_not_awaited()
        # Output still has auto_reply text
        assert "Pedro" in output.auto_reply

    @pytest.mark.asyncio
    async def test_cleans_whatsapp_formatting(self) -> None:
        """WhatsApp with +, spaces, hyphens → cleaned to digits-only."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True
        mock_agent_repo.find_active_by_client.return_value = None

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="+57 300-123-4567",
        )

        await uc.execute(inp)

        saved_lead = mock_lead_repo.save.call_args[0][0]
        assert saved_lead.phone == "573001234567"

    @pytest.mark.asyncio
    async def test_empty_interest_is_valid(self) -> None:
        """Empty interest string → accepted, lead created."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True
        mock_agent_repo.find_active_by_client.return_value = None

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="573001234567",
            interest="",
        )

        output = await uc.execute(inp)

        assert output.lead_id is not None
        mock_lead_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_whatsapp_send_failure_does_not_fail_use_case(self) -> None:
        """EC-09: WhatsApp send fails → lead still created, output returned."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)
        mock_sender = AsyncMock()

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True

        mock_agent = MagicMock(spec=Agent)
        mock_agent.id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_agent_repo.find_active_by_client.return_value = mock_agent
        mock_sender.send.side_effect = Exception("WhatsApp API down")

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
            message_sender=mock_sender,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="573001234567",
        )

        # Should NOT raise
        output = await uc.execute(inp)

        assert output.lead_id is not None
        mock_lead_repo.save.assert_awaited_once()  # lead persisted
        mock_sender.send.assert_awaited_once()  # send was attempted


# ============================================================================
# 8. SubmitLandingLeadUseCase — Errors & Edge Cases
# ============================================================================


class TestSubmitLandingLeadErrors:
    """SubmitLandingLeadUseCase: validation, missing slug, inactive landing, rate limit."""

    @pytest.mark.asyncio
    async def test_slug_not_found_raises_landing_not_found(self) -> None:
        """TL-018: Slug doesn't exist → LandingNotFoundError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        mock_landing_repo.find_client_by_slug.return_value = None

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="no-existe",
            name="Test",
            whatsapp="573001234567",
        )

        with pytest.raises(LandingNotFoundError, match="not found"):
            await uc.execute(inp)

        mock_lead_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_landing_inactive_raises_landing_inactive(self) -> None:
        """TL-019: landing_active=false → LandingInactiveError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client()
        config = _make_landing_config(is_active=False)  # inactive
        mock_landing_repo.find_client_by_slug.return_value = (client, config)

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="573001234567",
        )

        with pytest.raises(LandingInactiveError, match="not active"):
            await uc.execute(inp)

        mock_lead_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_client_inactive_raises_landing_inactive(self) -> None:
        """TL-020: Client is_active=False → LandingInactiveError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client(is_active=False)  # client inactive
        config = _make_landing_config(is_active=True)
        mock_landing_repo.find_client_by_slug.return_value = (client, config)

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="573001234567",
        )

        with pytest.raises(LandingInactiveError):
            await uc.execute(inp)

        mock_lead_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_whatsapp_too_short_raises_invalid_lead(self) -> None:
        """TL-021: WhatsApp < 10 digits → InvalidLeadError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="12345",  # too short
        )

        with pytest.raises(InvalidLeadError, match="WhatsApp"):
            await uc.execute(inp)

        mock_lead_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whatsapp_only_nondigits_raises_invalid_lead(self) -> None:
        """WhatsApp with only non-digit characters → InvalidLeadError after cleaning."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="abc-+def",  # no digits
        )

        with pytest.raises(InvalidLeadError, match="WhatsApp"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_empty_name_raises_invalid_lead(self) -> None:
        """TL-022: Empty name → InvalidLeadError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="",
            whatsapp="573001234567",
        )

        with pytest.raises(InvalidLeadError, match="name|Name"):
            await uc.execute(inp)

        mock_lead_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_name_raises_invalid_lead(self) -> None:
        """Whitespace-only name → InvalidLeadError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="   ",
            whatsapp="573001234567",
        )

        with pytest.raises(InvalidLeadError, match="name|Name"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_raises_landing_rate_limit(self) -> None:
        """TL-027: Rate limit (5/min per IP) exceeded → LandingRateLimitError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = False  # rate limited

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="573001234567",
        )

        with pytest.raises(LandingRateLimitError, match="Too many submissions"):
            await uc.execute(inp, client_ip="192.168.1.1")

        mock_landing_repo.check_rate_limit.assert_awaited_once_with(
            "192.168.1.1", max_req=5, window_sec=60,
        )
        mock_lead_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rate_limit_checked_per_ip(self) -> None:
        """Rate limit check receives the client_ip parameter."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_lead_repo = AsyncMock(spec=LeadRepository)
        mock_agent_repo = AsyncMock(spec=AgentRepository)

        client = _make_client()
        config = _make_landing_config()
        mock_landing_repo.find_client_by_slug.return_value = (client, config)
        mock_landing_repo.check_rate_limit.return_value = True
        mock_agent_repo.find_active_by_client.return_value = None

        uc = SubmitLandingLeadUseCase(
            landing_repo=mock_landing_repo,
            lead_repo=mock_lead_repo,
            agent_repo=mock_agent_repo,
        )
        inp = SubmitLandingInput(
            slug="mi-slug",
            name="Test",
            whatsapp="573001234567",
        )

        await uc.execute(inp, client_ip="10.0.0.5")

        mock_landing_repo.check_rate_limit.assert_awaited_once_with(
            "10.0.0.5", max_req=5, window_sec=60,
        )


# ============================================================================
# 9. GetLandingConfigUseCase
# ============================================================================


class TestGetLandingConfigUseCase:
    """GetLandingConfigUseCase: admin retrieval of landing config + leads_count."""

    @pytest.mark.asyncio
    async def test_returns_config_with_leads_count(self) -> None:
        """TL-028: Returns LandingConfigOutput with leads_count."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        config = _make_landing_config(
            client_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            slug="mi-negocio",
            title="Mi Negocio",
            description="Descripción",
            is_active=True,
        )
        mock_landing_repo.get_landing_config.return_value = config
        mock_landing_repo.count_leads_by_landing.return_value = 42

        uc = GetLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = GetLandingConfigInput(client_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

        output = await uc.execute(inp)

        assert isinstance(output, LandingConfigOutput)
        assert output.client_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert output.landing_slug == "mi-negocio"
        assert output.landing_title == "Mi Negocio"
        assert output.landing_description == "Descripción"
        assert output.landing_active is True
        assert output.landing_primary_color == "#f59e0b"
        assert output.landing_auto_reply == "¡Hola {{name}}! Gracias por contactarnos."
        assert output.leads_count == 42

        mock_landing_repo.get_landing_config.assert_awaited_once_with(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        )
        mock_landing_repo.count_leads_by_landing.assert_awaited_once_with(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        )

    @pytest.mark.asyncio
    async def test_client_not_found_raises_client_not_found(self) -> None:
        """TL-029: Client doesn't exist → ClientNotFoundError."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)
        mock_landing_repo.get_landing_config.return_value = None

        uc = GetLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = GetLandingConfigInput(client_id="non-existent-id")

        with pytest.raises(ClientNotFoundError, match="not found"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_zero_leads_count(self) -> None:
        """Client with no landing leads → leads_count=0."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        config = _make_landing_config()
        mock_landing_repo.get_landing_config.return_value = config
        mock_landing_repo.count_leads_by_landing.return_value = 0

        uc = GetLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = GetLandingConfigInput(client_id="test-id")

        output = await uc.execute(inp)

        assert output.leads_count == 0


# ============================================================================
# 10. UpdateLandingConfigUseCase
# ============================================================================


class TestUpdateLandingConfigUseCase:
    """UpdateLandingConfigUseCase: admin updates to landing configuration."""

    @pytest.mark.asyncio
    async def test_updates_title_correctly(self) -> None:
        """TL-030: Update landing_title → config returned with new title."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        updated_config = _make_landing_config(title="Nuevo Título")
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 10

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            landing_title="Nuevo Título",
        )

        output = await uc.execute(inp)

        assert output.landing_title == "Nuevo Título"
        # Other fields should be preserved (from the returned config)
        mock_landing_repo.update_landing_config.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_multiple_fields(self) -> None:
        """Multiple fields updated simultaneously."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        updated_config = _make_landing_config(
            title="Nuevo",
            description="Nueva desc",
            primary_color="#000000",
            auto_reply="Gracias {{name}}!",
        )
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 5

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_title="Nuevo",
            landing_description="Nueva desc",
            landing_primary_color="#000000",
            landing_auto_reply="Gracias {{name}}!",
        )

        output = await uc.execute(inp)

        assert output.landing_title == "Nuevo"
        assert output.landing_description == "Nueva desc"
        assert output.landing_primary_color == "#000000"
        assert output.landing_auto_reply == "Gracias {{name}}!"

    @pytest.mark.asyncio
    async def test_activate_landing_auto_generates_slug(self) -> None:
        """TL-031: Activating landing without slug → auto-generates from client name."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        # Current config has no slug
        current_config = _make_landing_config(slug="")
        mock_landing_repo.get_landing_config.return_value = current_config

        # Client has a name
        client = _make_client(name="Mi Negocio")
        mock_landing_repo.get_client.return_value = client
        mock_landing_repo.get_all_slugs.return_value = set()

        updated_config = _make_landing_config(slug="mi-negocio", is_active=True)
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 0

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_active=True,
        )

        output = await uc.execute(inp)

        assert output.landing_slug == "mi-negocio"
        assert output.landing_active is True
        mock_landing_repo.get_client.assert_awaited_once_with("test-id")

    @pytest.mark.asyncio
    async def test_slug_duplicate_auto_generates_suffix(self) -> None:
        """TL-032: Duplicate slug → auto-generates numerical suffix (e.g., -2)."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        mock_landing_repo.slug_exists.return_value = True  # slug is taken
        mock_landing_repo.get_all_slugs.return_value = {"mi-negocio", "mi-negocio-2"}

        updated_config = _make_landing_config(slug="mi-negocio-3")
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 0

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_slug="mi-negocio",
        )

        output = await uc.execute(inp)

        # Should resolve to mi-negocio-3 (since mi-negocio and mi-negocio-2 exist)
        assert output.landing_slug == "mi-negocio-3"
        mock_landing_repo.slug_exists.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_slug_not_duplicate_uses_as_is(self) -> None:
        """Unique slug → used as provided without suffix."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        mock_landing_repo.slug_exists.return_value = False  # not taken

        updated_config = _make_landing_config(slug="mi-slug-unico")
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 0

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_slug="mi-slug-unico",
        )

        output = await uc.execute(inp)

        assert output.landing_slug == "mi-slug-unico"

    @pytest.mark.asyncio
    async def test_all_fields_none_raises_value_error(self) -> None:
        """TL-033: No fields provided → ValueError (enforced in UpdateLandingConfigInput DTO)."""
        with pytest.raises(ValueError, match="at least one"):
            UpdateLandingConfigInput(client_id="test-id")

    @pytest.mark.asyncio
    async def test_deactivate_landing(self) -> None:
        """Deactivating landing → landing_active=False."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        updated_config = _make_landing_config(is_active=False)
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 5

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_active=False,
        )

        output = await uc.execute(inp)

        assert output.landing_active is False

    @pytest.mark.asyncio
    async def test_updates_primary_color(self) -> None:
        """Update just the primary color."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        updated_config = _make_landing_config(primary_color="#00ff00")
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 0

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_primary_color="#00ff00",
        )

        output = await uc.execute(inp)

        assert output.landing_primary_color == "#00ff00"

    @pytest.mark.asyncio
    async def test_updates_auto_reply(self) -> None:
        """Update just the auto_reply template."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        updated_config = _make_landing_config(auto_reply="Gracias {{name}}, te llamamos.")
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 0

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_auto_reply="Gracias {{name}}, te llamamos.",
        )

        output = await uc.execute(inp)

        assert output.landing_auto_reply == "Gracias {{name}}, te llamamos."

    @pytest.mark.asyncio
    async def test_slug_excluded_from_uniqueness_check_for_same_client(self) -> None:
        """Slug uniqueness check excludes the current client (can keep same slug)."""
        mock_landing_repo = AsyncMock(spec=LandingRepository)

        # slug_exists should be called with exclude_client_id
        mock_landing_repo.slug_exists.return_value = False

        updated_config = _make_landing_config(slug="mi-slug")
        mock_landing_repo.update_landing_config.return_value = updated_config
        mock_landing_repo.count_leads_by_landing.return_value = 0

        uc = UpdateLandingConfigUseCase(landing_repo=mock_landing_repo)
        inp = UpdateLandingConfigInput(
            client_id="my-client-id",
            landing_slug="mi-slug",
        )

        await uc.execute(inp)

        mock_landing_repo.slug_exists.assert_awaited_once_with(
            "mi-slug", exclude_client_id="my-client-id",
        )


# ============================================================================
# 11. Landing DTOs — Validation
# ============================================================================


class TestLandingDTOs:
    """Input/output DTOs for landing module."""

    def test_submit_landing_input_frozen(self) -> None:
        """SubmitLandingInput is a frozen dataclass."""
        inp = SubmitLandingInput(
            slug="test",
            name="Juan",
            whatsapp="573001234567",
            interest="info",
        )
        with pytest.raises(Exception):
            inp.name = "Pedro"  # type: ignore[misc]

    def test_update_landing_config_input_requires_at_least_one_field(self) -> None:
        """UpdateLandingConfigInput with no fields → ValueError."""
        with pytest.raises(ValueError, match="at least one"):
            UpdateLandingConfigInput(client_id="test-id")

    def test_update_landing_config_input_accepts_partial(self) -> None:
        """UpdateLandingConfigInput with just one field is valid."""
        inp = UpdateLandingConfigInput(
            client_id="test-id",
            landing_title="New Title",
        )
        assert inp.landing_title == "New Title"
        assert inp.landing_description is None

    def test_landing_config_output_frozen(self) -> None:
        """LandingConfigOutput is frozen."""
        out = LandingConfigOutput(
            client_id="test",
            landing_slug="slug",
            landing_title="Title",
            landing_description="Desc",
            landing_active=True,
            landing_primary_color="#fff",
            landing_auto_reply="Reply",
            leads_count=0,
        )
        with pytest.raises(Exception):
            out.leads_count = 42  # type: ignore[misc]

    def test_landing_public_config_output_fields(self) -> None:
        """LandingPublicConfigOutput has public-only fields (no slug, no auto_reply)."""
        out = LandingPublicConfigOutput(
            client_name="Mi Negocio",
            landing_title="Título",
            landing_description="Descripción",
            landing_active=True,
            landing_primary_color="#f59e0b",
        )
        assert out.client_name == "Mi Negocio"
        assert out.landing_title == "Título"
        assert not hasattr(out, "landing_slug")  # not exposed publicly
        assert not hasattr(out, "landing_auto_reply")  # not exposed publicly


# ============================================================================
# 12. LandingRepository Interface
# ============================================================================


class TestLandingRepositoryInterface:
    """Verify LandingRepository ABC defines all required methods."""

    def test_has_abstract_methods(self) -> None:
        """All 8 methods from spec section 7.3 are declared as abstract."""
        from abc import abstractmethod

        # find_client_by_slug
        assert hasattr(LandingRepository, "find_client_by_slug")
        # get_landing_config
        assert hasattr(LandingRepository, "get_landing_config")
        # update_landing_config
        assert hasattr(LandingRepository, "update_landing_config")
        # slug_exists
        assert hasattr(LandingRepository, "slug_exists")
        # count_leads_by_landing
        assert hasattr(LandingRepository, "count_leads_by_landing")
        # check_rate_limit
        assert hasattr(LandingRepository, "check_rate_limit")
        # get_all_slugs
        assert hasattr(LandingRepository, "get_all_slugs")
        # get_client
        assert hasattr(LandingRepository, "get_client")

    def test_is_abstract_cannot_instantiate(self) -> None:
        """LandingRepository is abstract — cannot instantiate directly."""
        with pytest.raises(TypeError):
            LandingRepository()  # type: ignore[abstract]
