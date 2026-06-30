"""Unit tests for Client application use cases (RED phase — TDD).

These tests import use case classes and DTOs that do NOT exist yet.
They define the expected behavior before any implementation is written.

Coverage: CreateClient, GetClient, ListClients, DeactivateClient, UpdateClient.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

# --- Application layer (does NOT exist yet — RED phase) ---
from app.application.client.create_client import CreateClientUseCase
from app.application.client.deactivate_client import DeactivateClientUseCase
from app.application.client.get_client import GetClientUseCase
from app.application.client.list_clients import ListClientsUseCase
from app.application.client.update_client import UpdateClientUseCase
from app.application.dtos import (
    ClientOutput,
    CreateClientInput,
    DeactivateClientInput,
    GetClientInput,
    ListClientsInput,
    UpdateClientInput,
)

# --- Domain layer (already exists) ---
from app.domain.client.entity import Client
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import (
    ClientNotFoundError,
    DomainError,
    InvalidClientError,
)
from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber


# ============================================================================
# Helpers
# ============================================================================

def _make_client(**overrides: object) -> Client:
    """Factory for Client entities with overridable fields.

    Creates a valid Client and then applies overrides via object.__setattr__
    for frozen/dataclass-managed fields. Timestamps default to 2026-01-01 UTC.
    """
    c = Client(
        name=str(overrides.get("name", "Test Client")),
        business_type=overrides.get("business_type", BusinessType("otro")),  # type: ignore[arg-type]
        whatsapp_number=overrides.get("whatsapp_number", WhatsAppNumber("573001234567")),  # type: ignore[arg-type]
    )
    if "id" in overrides:
        object.__setattr__(c, "id", overrides["id"])
    if "is_active" in overrides:
        c.is_active = bool(overrides["is_active"])
    if "created_at" in overrides:
        object.__setattr__(c, "created_at", overrides["created_at"])
    else:
        object.__setattr__(c, "created_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    if "updated_at" in overrides:
        object.__setattr__(c, "updated_at", overrides["updated_at"])
    else:
        object.__setattr__(c, "updated_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    return c


# ============================================================================
# CreateClientUseCase  (RF-01, RF-02)
# ============================================================================

class TestCreateClientUseCase:
    """RF-01 (happy), RF-02 (duplicate), EC-01–EC-04 (edge cases)."""

    @pytest.mark.asyncio
    async def test_creates_client_successfully(self) -> None:
        """RF-01: valid input, no duplicate → ClientOutput, save called."""
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_whatsapp.return_value = None

        uc = CreateClientUseCase(mock_repo)
        inp = CreateClientInput(
            name="Peluquería El Buen Corte",
            business_type="peluqueria",
            whatsapp_number="573001234567",
        )

        output = await uc.execute(inp)

        # Repository calls
        mock_repo.find_by_whatsapp.assert_awaited_once_with("573001234567")
        mock_repo.save.assert_awaited_once()

        # Output shape
        assert isinstance(output, ClientOutput)
        assert output.name == "Peluquería El Buen Corte"
        assert output.business_type == "peluqueria"
        assert output.whatsapp_number == "573001234567"
        assert output.is_active is True
        assert output.id  # non-empty UUID string

    @pytest.mark.asyncio
    async def test_raises_on_duplicate_whatsapp(self) -> None:
        """RF-02: existing WhatsApp → InvalidClientError, save not called."""
        existing = _make_client()
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_whatsapp.return_value = existing

        uc = CreateClientUseCase(mock_repo)
        inp = CreateClientInput(
            name="Some Biz",
            business_type="bar",
            whatsapp_number="573001234567",
        )

        with pytest.raises(InvalidClientError, match="WhatsApp number already registered"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_empty_name(self) -> None:
        """EC-01: empty name → InvalidClientError before touching repo."""
        mock_repo = AsyncMock(spec=ClientRepository)
        uc = CreateClientUseCase(mock_repo)

        inp = CreateClientInput(
            name="", business_type="bar", whatsapp_number="573001234567"
        )

        with pytest.raises(InvalidClientError, match="Client name cannot be empty"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_business_type(self) -> None:
        """EC-02: business_type not in VALID_TYPES → ValueError from VO."""
        mock_repo = AsyncMock(spec=ClientRepository)
        uc = CreateClientUseCase(mock_repo)

        inp = CreateClientInput(
            name="My Biz", business_type="colegio", whatsapp_number="573001234567"
        )

        with pytest.raises(InvalidClientError, match="Invalid business type"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_whatsapp_too_short(self) -> None:
        """EC-03: WhatsApp with < 10 digits → ValueError from VO."""
        mock_repo = AsyncMock(spec=ClientRepository)
        uc = CreateClientUseCase(mock_repo)

        inp = CreateClientInput(
            name="My Biz", business_type="otro", whatsapp_number="12345"
        )

        with pytest.raises(ValueError, match="WhatsApp number must be digits only"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cleans_whatsapp_special_chars(self) -> None:
        """EC-04: WhatsApp with +, spaces, hyphens → cleaned → success."""
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_whatsapp.return_value = None

        uc = CreateClientUseCase(mock_repo)
        inp = CreateClientInput(
            name="My Biz",
            business_type="otro",
            whatsapp_number="+57 300-123-4567",
        )

        output = await uc.execute(inp)

        assert output.whatsapp_number == "573001234567"
        mock_repo.find_by_whatsapp.assert_awaited_once_with("573001234567")


# ============================================================================
# GetClientUseCase  (RF-03, RF-04)
# ============================================================================

class TestGetClientUseCase:
    """RF-03 (by ID), RF-04 (by WhatsApp), EC-05–EC-08."""

    CLIENT_ID = "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_finds_by_id_successfully(self) -> None:
        """RF-03: existing client_id → ClientOutput."""
        client = _make_client(id=uuid.UUID(self.CLIENT_ID))
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = GetClientUseCase(mock_repo)
        inp = GetClientInput(client_id=self.CLIENT_ID)

        output = await uc.execute(inp)

        assert output.id == self.CLIENT_ID
        assert output.name == client.name
        mock_repo.find_by_id.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_client_not_found_by_id(self) -> None:
        """EC-07: non-existent client_id → ClientNotFoundError."""
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = None

        uc = GetClientUseCase(mock_repo)
        inp = GetClientInput(client_id=self.CLIENT_ID)

        with pytest.raises(ClientNotFoundError, match="Client not found"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_finds_by_whatsapp_successfully(self) -> None:
        """RF-04: existing WhatsApp → ClientOutput."""
        client = _make_client(whatsapp_number=WhatsAppNumber("573001234567"))
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_whatsapp.return_value = client

        uc = GetClientUseCase(mock_repo)
        inp = GetClientInput(whatsapp="573001234567")

        output = await uc.execute(inp)

        assert output.whatsapp_number == "573001234567"
        mock_repo.find_by_whatsapp.assert_awaited_once_with("573001234567")

    @pytest.mark.asyncio
    async def test_raises_when_client_not_found_by_whatsapp(self) -> None:
        """EC-08: non-existent WhatsApp → ClientNotFoundError."""
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_whatsapp.return_value = None

        uc = GetClientUseCase(mock_repo)
        inp = GetClientInput(whatsapp="573001234567")

        with pytest.raises(ClientNotFoundError, match="Client not found by WhatsApp"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_raises_on_invalid_uuid_client_id(self) -> None:
        """EC-05: non-UUID client_id → InvalidClientError from ClientId VO."""
        mock_repo = AsyncMock(spec=ClientRepository)
        uc = GetClientUseCase(mock_repo)
        inp = GetClientInput(client_id="not-a-uuid")

        with pytest.raises(InvalidClientError, match="Invalid ClientId"):
            await uc.execute(inp)


# ============================================================================
# ListClientsUseCase  (RF-05)
# ============================================================================

class TestListClientsUseCase:
    """RF-05, EC-09–EC-11."""

    @pytest.mark.asyncio
    async def test_lists_active_clients(self) -> None:
        """Happy path: returns list[ClientOutput] with pagination."""
        clients = [
            _make_client(id=uuid.uuid4(), name=f"Client {i}") for i in range(3)
        ]
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.list_active.return_value = clients

        uc = ListClientsUseCase(mock_repo)
        inp = ListClientsInput(limit=10, offset=5)

        outputs = await uc.execute(inp)

        assert len(outputs) == 3
        assert all(isinstance(o, ClientOutput) for o in outputs)
        assert outputs[0].name == "Client 0"
        assert outputs[2].name == "Client 2"
        mock_repo.list_active.assert_awaited_once_with(10, 5)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_clients(self) -> None:
        """EC-11: no active clients → []."""
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.list_active.return_value = []

        uc = ListClientsUseCase(mock_repo)
        inp = ListClientsInput()

        outputs = await uc.execute(inp)

        assert outputs == []
        # Default pagination
        mock_repo.list_active.assert_awaited_once_with(50, 0)

    @pytest.mark.asyncio
    async def test_raises_on_limit_zero(self) -> None:
        """EC-09: limit=0 → InvalidClientError."""
        mock_repo = AsyncMock(spec=ClientRepository)
        uc = ListClientsUseCase(mock_repo)
        inp = ListClientsInput(limit=0)

        with pytest.raises(InvalidClientError, match="limit must be >= 1"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_raises_on_negative_offset(self) -> None:
        """EC-10: offset=-5 → InvalidClientError."""
        mock_repo = AsyncMock(spec=ClientRepository)
        uc = ListClientsUseCase(mock_repo)
        inp = ListClientsInput(offset=-5)

        with pytest.raises(InvalidClientError, match="offset must be >= 0"):
            await uc.execute(inp)


# ============================================================================
# DeactivateClientUseCase  (RF-06, RF-07)
# ============================================================================

class TestDeactivateClientUseCase:
    """RF-06 (happy), RF-07 (not found), EC-12 (idempotent)."""

    CLIENT_ID = "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_deactivates_client_successfully(self) -> None:
        """RF-06: active client → deactivated, is_active=False in output."""
        client = _make_client(id=uuid.UUID(self.CLIENT_ID), is_active=True)
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = DeactivateClientUseCase(mock_repo)
        inp = DeactivateClientInput(client_id=self.CLIENT_ID)

        output = await uc.execute(inp)

        assert output.is_active is False
        assert client.is_active is False
        assert output.id == self.CLIENT_ID
        mock_repo.save.assert_awaited_once_with(client)

    @pytest.mark.asyncio
    async def test_raises_when_client_not_found(self) -> None:
        """RF-07: non-existent client → ClientNotFoundError."""
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = None

        uc = DeactivateClientUseCase(mock_repo)
        inp = DeactivateClientInput(client_id=self.CLIENT_ID)

        with pytest.raises(ClientNotFoundError):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_deactivate_is_idempotent(self) -> None:
        """EC-12: already deactivated client → still succeeds, is_active=False."""
        client = _make_client(is_active=False)
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = DeactivateClientUseCase(mock_repo)
        inp = DeactivateClientInput(client_id=str(client.id))

        output = await uc.execute(inp)

        assert output.is_active is False
        mock_repo.save.assert_awaited_once_with(client)


# ============================================================================
# UpdateClientUseCase  (RF-08)
# ============================================================================

class TestUpdateClientUseCase:
    """RF-08, EC-13–EC-16."""

    CLIENT_ID = "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_updates_name_only(self) -> None:
        """EC-13: only name provided → name updated, WhatsApp unchanged."""
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            name="Old Name",
            whatsapp_number=WhatsAppNumber("573001234567"),
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = UpdateClientUseCase(mock_repo)
        inp = UpdateClientInput(client_id=self.CLIENT_ID, name="New Name")

        output = await uc.execute(inp)

        assert output.name == "New Name"
        assert output.whatsapp_number == "573001234567"
        assert client.name == "New Name"
        mock_repo.save.assert_awaited_once_with(client)

    @pytest.mark.asyncio
    async def test_updates_whatsapp_only(self) -> None:
        """EC-14: only WhatsApp provided → WhatsApp updated, name unchanged."""
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            name="My Biz",
            whatsapp_number=WhatsAppNumber("573001234567"),
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client
        mock_repo.find_by_whatsapp.return_value = None

        uc = UpdateClientUseCase(mock_repo)
        inp = UpdateClientInput(
            client_id=self.CLIENT_ID, whatsapp_number="573009876543"
        )

        output = await uc.execute(inp)

        assert output.name == "My Biz"
        assert output.whatsapp_number == "573009876543"
        assert str(client.whatsapp_number) == "573009876543"
        mock_repo.save.assert_awaited_once_with(client)

    @pytest.mark.asyncio
    async def test_updates_both_name_and_whatsapp(self) -> None:
        """Both fields provided → both updated."""
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            name="Old Name",
            whatsapp_number=WhatsAppNumber("573001234567"),
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client
        mock_repo.find_by_whatsapp.return_value = None

        uc = UpdateClientUseCase(mock_repo)
        inp = UpdateClientInput(
            client_id=self.CLIENT_ID,
            name="New Name",
            whatsapp_number="573009876543",
        )

        output = await uc.execute(inp)

        assert output.name == "New Name"
        assert output.whatsapp_number == "573009876543"
        mock_repo.save.assert_awaited_once_with(client)

    @pytest.mark.asyncio
    async def test_raises_on_duplicate_whatsapp_different_client(self) -> None:
        """EC-15: WhatsApp already used by another client → InvalidClientError."""
        client = _make_client(id=uuid.UUID(self.CLIENT_ID))
        other = _make_client(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222")
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client
        mock_repo.find_by_whatsapp.return_value = other  # different client!

        uc = UpdateClientUseCase(mock_repo)
        inp = UpdateClientInput(
            client_id=self.CLIENT_ID, whatsapp_number="573001234567"
        )

        with pytest.raises(InvalidClientError, match="WhatsApp number already registered"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_allows_same_whatsapp_on_same_client(self) -> None:
        """EC-16: same WhatsApp as current client → allowed (not a duplicate)."""
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            whatsapp_number=WhatsAppNumber("573001234567"),
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client
        # find_by_whatsapp returns the SAME client
        mock_repo.find_by_whatsapp.return_value = client

        uc = UpdateClientUseCase(mock_repo)
        inp = UpdateClientInput(
            client_id=self.CLIENT_ID, whatsapp_number="573001234567"
        )

        output = await uc.execute(inp)

        assert output.whatsapp_number == "573001234567"
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_client_not_found(self) -> None:
        """Non-existent client_id → ClientNotFoundError."""
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = None

        uc = UpdateClientUseCase(mock_repo)
        inp = UpdateClientInput(client_id=self.CLIENT_ID, name="New Name")

        with pytest.raises(ClientNotFoundError):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_empty_name_update(self) -> None:
        """Updating name to empty string → ValueError from domain entity."""
        client = _make_client(id=uuid.UUID(self.CLIENT_ID), name="Old Name")
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = UpdateClientUseCase(mock_repo)
        inp = UpdateClientInput(client_id=self.CLIENT_ID, name="")

        with pytest.raises(InvalidClientError, match="Client name cannot be empty"):
            await uc.execute(inp)


# ============================================================================
# Client DTO validation  (post_init checks)
# ============================================================================

class TestClientDTOValidation:
    """DTO __post_init__ guards — happen before use case execution."""

    def test_get_client_input_requires_id_or_whatsapp(self) -> None:
        """Both client_id and whatsapp None → ValueError on construction."""
        with pytest.raises(ValueError, match="Must provide client_id or whatsapp"):
            GetClientInput()

    def test_update_client_input_requires_at_least_one_field(self) -> None:
        """Both name and whatsapp_number None → ValueError on construction."""
        with pytest.raises(
            ValueError, match="Must provide at least one field to update"
        ):
            UpdateClientInput(client_id="11111111-1111-1111-1111-111111111111")

    def test_get_client_input_allows_only_client_id(self) -> None:
        """Only client_id provided → DTO created successfully."""
        inp = GetClientInput(client_id="11111111-1111-1111-1111-111111111111")
        assert inp.client_id == "11111111-1111-1111-1111-111111111111"
        assert inp.whatsapp is None

    def test_get_client_input_allows_only_whatsapp(self) -> None:
        """Only whatsapp provided → DTO created successfully."""
        inp = GetClientInput(whatsapp="573001234567")
        assert inp.client_id is None
        assert inp.whatsapp == "573001234567"
