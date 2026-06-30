"""Unit tests for the Templates module (RED phase — TDD).

These tests import classes from the Templates module that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage:
  - Template data integrity (all 10 templates, field validation)
  - TemplateService (list, get by slug, errors)
  - ApplyTemplateUseCase (creates client + agent, validation, errors)
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

# --- Templates infrastructure (does NOT exist yet — RED phase) ---
from app.infrastructure.templates.data import (
    TEMPLATES,
    TEMPLATES_BY_SLUG,
    TemplateDef,
    TemplateService,
    ToolDef,
)

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.templates.apply_template import ApplyTemplateUseCase
from app.application.dtos import (
    ApplyTemplateInput,
    ApplyTemplateOutput,
    TemplateItemOutput,
)

# --- Domain layer (already exists) ---
from app.domain.shared.errors import (
    InvalidTemplateError,
    TemplateNotFoundError,
)
from app.domain.shared.value_objects import BusinessType
from app.domain.client.repository import ClientRepository
from app.domain.agent.repository import AgentRepository


# ============================================================================
# Constants — expected values from spec
# ============================================================================

EXPECTED_TEMPLATE_COUNT = 10

EXPECTED_SLUGS: frozenset[str] = frozenset({
    "restaurante",
    "peluqueria",
    "clinica",
    "tienda",
    "inmobiliaria",
    "gimnasio",
    "contador",
    "taller",
    "hotel",
    "ecommerce",
})

# Per spec section 5.1: expanded BusinessType.VALID_TYPES
EXPANDED_VALID_TYPES: frozenset[str] = frozenset({
    "peluqueria", "bar", "restaurante", "contador",
    "tienda", "gimnasio", "clinica", "otro",
    "inmobiliaria", "taller", "hotel", "ecommerce",
})

_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


# ============================================================================
# Data Integrity  (TC-001 to TC-010)
# ============================================================================


class TestTemplateDataIntegrity:
    """Validate the 10 predefined templates match spec requirements."""

    def test_all_10_templates_are_defined(self) -> None:
        """TC-001: Exactly 10 templates exist."""
        assert len(TEMPLATES) == EXPECTED_TEMPLATE_COUNT

    def test_each_template_has_unique_slug(self) -> None:
        """TC-002: All slugs are unique across templates."""
        slugs = [t.slug for t in TEMPLATES]
        assert len(slugs) == len(set(slugs)), "Duplicate slug found"

    def test_each_slug_is_lowercase_alphanumeric(self) -> None:
        """TC-003: Each slug matches ^[a-z][a-z0-9_]*$ (lowercase only)."""
        for t in TEMPLATES:
            assert _SLUG_PATTERN.match(t.slug), (
                f"Slug '{t.slug}' is not lowercase alphanumeric"
            )

    def test_each_slug_is_in_expected_set(self) -> None:
        """All 10 slugs match the spec-defined slugs."""
        slugs = {t.slug for t in TEMPLATES}
        assert slugs == EXPECTED_SLUGS, f"Expected {EXPECTED_SLUGS}, got {slugs}"

    def test_each_template_has_non_empty_emoji(self) -> None:
        """TC-004: Every template has a non-empty emoji."""
        for t in TEMPLATES:
            assert t.emoji and t.emoji.strip(), (
                f"Template '{t.slug}' has empty emoji"
            )

    def test_each_template_has_non_empty_name(self) -> None:
        """TC-005: Every template has a non-empty name."""
        for t in TEMPLATES:
            assert t.name and t.name.strip(), (
                f"Template '{t.slug}' has empty name"
            )

    def test_each_template_has_non_empty_description(self) -> None:
        """TC-006: Every template has a non-empty description."""
        for t in TEMPLATES:
            assert t.description and t.description.strip(), (
                f"Template '{t.slug}' has empty description"
            )

    def test_each_template_has_valid_business_type(self) -> None:
        """TC-007: Every template's business_type is in VALID_TYPES.

        This also validates that the expanded set (spec section 5.1)
        is properly configured: inmobiliaria, taller, hotel, ecommerce
        must be accepted by BusinessType.
        """
        for t in TEMPLATES:
            btype = t.client_config.business_type
            assert btype in EXPANDED_VALID_TYPES, (
                f"Template '{t.slug}' has invalid business_type '{btype}'. "
                f"Must be one of {sorted(EXPANDED_VALID_TYPES)}"
            )
            # Also validates the VO can construct successfully
            BusinessType(btype)

    def test_each_template_personality_is_at_least_10_chars(self) -> None:
        """TC-008: Every template's personality is >= 10 characters."""
        for t in TEMPLATES:
            personality = t.agent_config.personality
            assert len(personality.strip()) >= 10, (
                f"Template '{t.slug}' personality is too short "
                f"({len(personality.strip())} chars, need >= 10)"
            )

    def test_each_template_has_at_least_one_tool(self) -> None:
        """TC-009: Every template defines at least 1 tool."""
        for t in TEMPLATES:
            assert len(t.agent_config.tools) >= 1, (
                f"Template '{t.slug}' has no tools"
            )

    def test_each_tool_has_non_empty_fields(self) -> None:
        """TC-010: Every tool has non-empty name, description, and endpoint."""
        for t in TEMPLATES:
            for tool in t.agent_config.tools:
                assert tool.name and tool.name.strip(), (
                    f"Template '{t.slug}' has a tool with empty name"
                )
                assert tool.description and tool.description.strip(), (
                    f"Template '{t.slug}' tool '{tool.name}' has empty description"
                )
                assert tool.endpoint and tool.endpoint.strip(), (
                    f"Template '{t.slug}' tool '{tool.name}' has empty endpoint"
                )


# ============================================================================
# TemplateService  (TC-011 to TC-014)
# ============================================================================


class TestTemplateService:
    """TemplateService: list_templates, get_template, TEMPLATES_BY_SLUG."""

    def setup_method(self) -> None:
        self.service = TemplateService()

    def test_list_templates_returns_all_10(self) -> None:
        """TC-011: TemplateService.list_templates() returns 10 templates."""
        result = self.service.list_templates()
        assert isinstance(result, list)
        assert len(result) == EXPECTED_TEMPLATE_COUNT

    def test_list_templates_returns_list_of_TemplateDef(self) -> None:
        """Each item in list_templates() is a TemplateDef instance."""
        result = self.service.list_templates()
        for t in result:
            assert isinstance(t, TemplateDef)

    def test_get_template_returns_by_slug(self) -> None:
        """TC-012: get_template('restaurante') returns the correct template."""
        result = self.service.get_template("restaurante")
        assert isinstance(result, TemplateDef)
        assert result.slug == "restaurante"
        assert result.name == "Restaurante"

    def test_get_template_returns_each_slug(self) -> None:
        """All 10 slugs can be retrieved via get_template()."""
        for expected_slug in EXPECTED_SLUGS:
            result = self.service.get_template(expected_slug)
            assert result.slug == expected_slug

    def test_get_template_with_invalid_slug_raises_error(self) -> None:
        """TC-013: get_template('xyz') raises TemplateNotFoundError."""
        with pytest.raises(TemplateNotFoundError, match="not found"):
            self.service.get_template("xyz-non-existent")

    def test_get_template_with_empty_slug_raises_error(self) -> None:
        """Empty slug should also raise TemplateNotFoundError."""
        with pytest.raises(TemplateNotFoundError):
            self.service.get_template("")

    def test_templates_by_slug_length_matches(self) -> None:
        """TC-014: TEMPLATES_BY_SLUG has same length as TEMPLATES."""
        assert len(TEMPLATES_BY_SLUG) == len(TEMPLATES)

    def test_templates_by_slug_keys_are_all_slugs(self) -> None:
        """TEMPLATES_BY_SLUG contains every template slug."""
        slugs = {t.slug for t in TEMPLATES}
        assert set(TEMPLATES_BY_SLUG.keys()) == slugs

    def test_template_service_validate_returns_true_for_valid(self) -> None:
        """validate_template() returns True for a known slug."""
        result = self.service.validate_template("restaurante")
        assert result is True

    def test_template_service_validate_returns_false_for_invalid(self) -> None:
        """validate_template() returns False for an unknown slug."""
        result = self.service.validate_template("no-existe")
        assert result is False


# ============================================================================
# ApplyTemplateUseCase  (TC-015 to TC-023)
# ============================================================================


class TestApplyTemplateUseCase:
    """ApplyTemplateUseCase: creates Client + Agent from a template."""

    VALID_WHATSAPP = "5491122334455"

    @pytest.fixture
    def mock_client_repo(self) -> AsyncMock:
        return AsyncMock(spec=ClientRepository)

    @pytest.fixture
    def mock_agent_repo(self) -> AsyncMock:
        return AsyncMock(spec=AgentRepository)

    @pytest.fixture
    def use_case(
        self,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> ApplyTemplateUseCase:
        return ApplyTemplateUseCase(
            template_service=TemplateService(),
            client_repo=mock_client_repo,
            agent_repo=mock_agent_repo,
        )

    @pytest.mark.asyncio
    async def test_creates_client_with_correct_business_type(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-015: Apply 'restaurante' → client has business_type='restaurante'."""
        inp = ApplyTemplateInput(
            slug="restaurante",
            name="Parrilla El Gaucho",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        output = await use_case.execute(inp)

        assert output.client.business_type == "restaurante"
        mock_client_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_agent_with_tools_from_template(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-016: Agent tools match the template's tool definitions."""
        inp = ApplyTemplateInput(
            slug="restaurante",
            name="Parrilla El Gaucho",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        output = await use_case.execute(inp)
        template = TemplateService().get_template("restaurante")
        expected_tool_names = {t.name for t in template.agent_config.tools}

        actual_tool_names = {t.name for t in output.agent.tools}

        assert actual_tool_names == expected_tool_names
        assert len(output.agent.tools) == len(template.agent_config.tools)
        mock_agent_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_agent_with_personality_from_template(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-017: Agent personality matches the template's personality."""
        inp = ApplyTemplateInput(
            slug="peluqueria",
            name="Corte Fino",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        output = await use_case.execute(inp)
        template = TemplateService().get_template("peluqueria")

        assert output.agent.personality == template.agent_config.personality
        mock_agent_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_on_empty_slug(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-018: Empty slug → InvalidTemplateError, repos not called."""
        inp = ApplyTemplateInput(
            slug="",
            name="My Business",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        with pytest.raises(InvalidTemplateError, match="slug is required"):
            await use_case.execute(inp)

        mock_client_repo.save.assert_not_awaited()
        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_whitespace_slug(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """Whitespace-only slug → InvalidTemplateError."""
        inp = ApplyTemplateInput(
            slug="   ",
            name="My Business",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        with pytest.raises(InvalidTemplateError, match="slug is required"):
            await use_case.execute(inp)

        mock_client_repo.save.assert_not_awaited()
        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_empty_name(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-019: Empty name → InvalidTemplateError, repos not called."""
        inp = ApplyTemplateInput(
            slug="restaurante",
            name="",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        with pytest.raises(InvalidTemplateError, match="name cannot be empty"):
            await use_case.execute(inp)

        mock_client_repo.save.assert_not_awaited()
        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_whitespace_name(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """Whitespace-only name → InvalidTemplateError."""
        inp = ApplyTemplateInput(
            slug="restaurante",
            name="   ",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        with pytest.raises(InvalidTemplateError, match="name cannot be empty"):
            await use_case.execute(inp)

        mock_client_repo.save.assert_not_awaited()
        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_non_existent_slug(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-020: Non-existent slug → TemplateNotFoundError, repos not called."""
        inp = ApplyTemplateInput(
            slug="no-existe",
            name="My Business",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        with pytest.raises(TemplateNotFoundError, match="Template 'no-existe' not found"):
            await use_case.execute(inp)

        mock_client_repo.save.assert_not_awaited()
        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_output_contains_valid_client_and_agent(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-021: ApplyTemplateOutput has client + agent with correct fields."""
        inp = ApplyTemplateInput(
            slug="tienda",
            name="Mi Tienda",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        output = await use_case.execute(inp)

        assert isinstance(output, ApplyTemplateOutput)
        assert output.template_slug == "tienda"
        assert output.message == (
            "Plantilla aplicada correctamente. Cliente y agente creados."
        )

        # Client fields
        assert output.client.name == "Mi Tienda"
        assert output.client.business_type == "tienda"
        assert output.client.whatsapp_number == self.VALID_WHATSAPP
        assert output.client.is_active is True
        assert output.client.id  # non-empty UUID string

        # Agent fields
        assert output.agent.client_id == output.client.id
        assert output.agent.is_active is True
        assert output.agent.id  # non-empty UUID string

    @pytest.mark.asyncio
    async def test_client_repo_save_called_once(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-022: client_repo.save() is called exactly 1 time on success."""
        inp = ApplyTemplateInput(
            slug="hotel",
            name="Gran Hotel",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        await use_case.execute(inp)

        mock_client_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_agent_repo_save_called_once(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """TC-023: agent_repo.save() is called exactly 1 time on success."""
        inp = ApplyTemplateInput(
            slug="contador",
            name="Estudio Perez",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        await use_case.execute(inp)

        mock_agent_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_order_client_before_agent(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """Client is saved before Agent (call order enforced)."""
        inp = ApplyTemplateInput(
            slug="gimnasio",
            name="Fit Gym",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        await use_case.execute(inp)

        # Verify call order: client_repo.save before agent_repo.save
        client_call = mock_client_repo.save.await_args
        agent_call = mock_agent_repo.save.await_args
        assert client_call is not None, "client_repo.save was never called"
        assert agent_call is not None, "agent_repo.save was never called"

        # Client saved first
        method_calls = mock_client_repo.mock_calls + mock_agent_repo.mock_calls
        save_calls = (
            i for i, call in enumerate(method_calls)
            if call[0] == "save"
        )
        client_save_index = next(save_calls)
        agent_save_index = next(save_calls)
        assert client_save_index < agent_save_index

    @pytest.mark.asyncio
    async def test_agent_name_follows_convention(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """Agent name is 'Asistente {template.name}' per spec."""
        inp = ApplyTemplateInput(
            slug="inmobiliaria",
            name="Casas y Mas",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        output = await use_case.execute(inp)

        assert output.agent.name == "Asistente Inmobiliaria"

    @pytest.mark.asyncio
    async def test_raises_on_whatsapp_too_short(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """WhatsApp < 10 digits → ValueError from WhatsAppNumber VO."""
        inp = ApplyTemplateInput(
            slug="restaurante",
            name="Mi Restaurant",
            whatsapp_number="12345",  # only 5 digits
        )

        with pytest.raises((ValueError, InvalidTemplateError), match="WhatsApp"):
            await use_case.execute(inp)

        mock_client_repo.save.assert_not_awaited()
        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_whatsapp_with_letters(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """WhatsApp with non-digit chars → ValueError from WhatsAppNumber VO."""
        inp = ApplyTemplateInput(
            slug="restaurante",
            name="Mi Restaurant",
            whatsapp_number="54911ABC2345",
        )

        with pytest.raises((ValueError, InvalidTemplateError), match="digits"):
            await use_case.execute(inp)

        mock_client_repo.save.assert_not_awaited()
        mock_agent_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cleans_whatsapp_special_chars(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """WhatsApp with +, spaces, hyphens is cleaned to digits only."""
        inp = ApplyTemplateInput(
            slug="restaurante",
            name="Mi Restaurant",
            whatsapp_number="+54 911-2233-4455",
        )

        output = await use_case.execute(inp)

        assert output.client.whatsapp_number == "5491122334455"
        mock_client_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_each_template_creates_matching_business_type(
        self,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """Applying each of the 10 templates sets the correct business_type."""
        for slug in EXPECTED_SLUGS:
            mock_client_repo.reset_mock()
            mock_agent_repo.reset_mock()

            uc = ApplyTemplateUseCase(
                template_service=TemplateService(),
                client_repo=mock_client_repo,
                agent_repo=mock_agent_repo,
            )
            inp = ApplyTemplateInput(
                slug=slug,
                name=f"Test {slug}",
                whatsapp_number="5491122334455",
            )

            output = await uc.execute(inp)
            template = TemplateService().get_template(slug)
            expected_btype = template.client_config.business_type

            assert output.client.business_type == expected_btype, (
                f"Template '{slug}' expected business_type '{expected_btype}', "
                f"got '{output.client.business_type}'"
            )

    @pytest.mark.asyncio
    async def test_output_is_frozen_dataclass(
        self,
        use_case: ApplyTemplateUseCase,
        mock_client_repo: AsyncMock,
        mock_agent_repo: AsyncMock,
    ) -> None:
        """ApplyTemplateOutput and its nested DTOs are immutable."""
        inp = ApplyTemplateInput(
            slug="hotel",
            name="Hotel Test",
            whatsapp_number=self.VALID_WHATSAPP,
        )

        output = await use_case.execute(inp)

        with pytest.raises(AttributeError):
            output.message = "changed"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            output.client.name = "changed"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            output.agent.name = "changed"  # type: ignore[misc]
