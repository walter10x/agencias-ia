from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.auth.approve_client import ApproveClientUseCase
from app.application.auth.connect_whatsapp import ConnectWhatsappUseCase
from app.application.auth.reject_client import RejectClientUseCase
from app.application.auth.disconnect_whatsapp import DisconnectWhatsappUseCase
from app.application.dtos import (
    AdminClientOutput,
    ApproveClientInput,
    ConnectWhatsappInput,
    DisconnectWhatsappInput,
    RejectClientInput,
)
from app.domain.client.entity import Client
from app.domain.client.enums import ClientRole, ClientStatus
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import AuthError, ForbiddenError, InvalidClientError
from app.domain.shared.value_objects import (
    BusinessType,
    Email,
    PasswordHash,
    WhatsAppNumber,
)


_VALID_FAKE_HASH = "$2b$12$" + "a" * 53


def _make_client(**overrides: object) -> Client:
    c = Client(
        name=str(overrides.get("name", "Test Client")),
        business_type=overrides.get("business_type", BusinessType("otro")),
        whatsapp_number=overrides.get("whatsapp_number", WhatsAppNumber("573001234567")),
    )
    if "id" in overrides:
        object.__setattr__(c, "id", overrides["id"])
    if "is_active" in overrides:
        c.is_active = bool(overrides["is_active"])
    if "email" in overrides:
        object.__setattr__(c, "email", overrides["email"])
    if "password_hash" in overrides:
        object.__setattr__(c, "password_hash", overrides["password_hash"])
    if "role" in overrides:
        c.role = ClientRole(overrides["role"])
    if "status" in overrides:
        c.status = ClientStatus(overrides["status"])
    if "phone_number_id" in overrides:
        c.phone_number_id = str(overrides["phone_number_id"])
    if "whatsapp_connected" in overrides:
        c.whatsapp_connected = bool(overrides["whatsapp_connected"])
    if "plan" in overrides:
        c.plan = str(overrides["plan"])
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
# ApproveClientUseCase
# ============================================================================


class TestApproveClientUseCase:
    CLIENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    @pytest.mark.asyncio
    async def test_approve_pending_client(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.PENDING,
            is_active=True,
            phone_number_id="",
            whatsapp_connected=False,
            plan="free",
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = ApproveClientUseCase(mock_repo)
        inp = ApproveClientInput(client_id=self.CLIENT_ID)

        output = await uc.execute(inp, current_role="superadmin")

        assert isinstance(output, AdminClientOutput)
        assert output.status == "approved"
        assert output.email == "test@example.com"

        mock_repo.find_by_id.assert_awaited_once()
        mock_repo.save.assert_awaited_once()

        saved = mock_repo.save.call_args[0][0]
        assert saved.status == ClientStatus.APPROVED
        assert saved.is_active is True

    @pytest.mark.asyncio
    async def test_approve_not_found(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = None

        uc = ApproveClientUseCase(mock_repo)
        inp = ApproveClientInput(client_id=self.CLIENT_ID)

        with pytest.raises(InvalidClientError, match="not found"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approve_already_active(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.ACTIVE,
            is_active=True,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = ApproveClientUseCase(mock_repo)
        inp = ApproveClientInput(client_id=self.CLIENT_ID)

        with pytest.raises(InvalidClientError, match="already approved or not pending"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approve_non_superadmin_raises(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)

        uc = ApproveClientUseCase(mock_repo)
        inp = ApproveClientInput(client_id=self.CLIENT_ID)

        with pytest.raises(ForbiddenError, match="Only superadmin"):
            await uc.execute(inp, current_role="client_admin")

        mock_repo.find_by_id.assert_not_awaited()


# ============================================================================
# RejectClientUseCase
# ============================================================================


class TestRejectClientUseCase:
    CLIENT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    @pytest.mark.asyncio
    async def test_reject_pending_client(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.PENDING,
            is_active=True,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = RejectClientUseCase(mock_repo)
        inp = RejectClientInput(client_id=self.CLIENT_ID)

        output = await uc.execute(inp, current_role="superadmin")

        assert isinstance(output, AdminClientOutput)
        assert output.status == "inactive"

        mock_repo.save.assert_awaited_once()
        saved = mock_repo.save.call_args[0][0]
        assert saved.status == ClientStatus.INACTIVE
        assert saved.is_active is False

    @pytest.mark.asyncio
    async def test_reject_already_inactive(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.INACTIVE,
            is_active=False,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = RejectClientUseCase(mock_repo)
        inp = RejectClientInput(client_id=self.CLIENT_ID)

        with pytest.raises(InvalidClientError, match="not pending"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.save.assert_not_awaited()


# ============================================================================
# DisconnectWhatsappUseCase
# ============================================================================


class TestDisconnectWhatsappUseCase:
    CLIENT_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    @pytest.mark.asyncio
    async def test_disconnect_active_client(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.ACTIVE,
            is_active=True,
            phone_number_id="123456789",
            whatsapp_connected=True,
            plan="free",
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = DisconnectWhatsappUseCase(mock_repo)
        inp = DisconnectWhatsappInput(client_id=self.CLIENT_ID)

        output = await uc.execute(inp, current_role="superadmin")

        assert isinstance(output, AdminClientOutput)
        assert output.whatsapp_connected is False

        mock_repo.save.assert_awaited_once()
        saved = mock_repo.save.call_args[0][0]
        assert saved.whatsapp_connected is False
        assert saved.phone_number_id == ""

    @pytest.mark.asyncio
    async def test_disconnect_pending_client(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.PENDING,
            is_active=True,
            phone_number_id="",
            whatsapp_connected=False,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = DisconnectWhatsappUseCase(mock_repo)
        inp = DisconnectWhatsappInput(client_id=self.CLIENT_ID)

        with pytest.raises(InvalidClientError, match="not connected"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disconnect_non_superadmin_raises(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)

        uc = DisconnectWhatsappUseCase(mock_repo)
        inp = DisconnectWhatsappInput(client_id=self.CLIENT_ID)

        with pytest.raises(ForbiddenError, match="Only superadmin"):
            await uc.execute(inp, current_role="client_admin")

        mock_repo.find_by_id.assert_not_awaited()


# ============================================================================
# ConnectWhatsappUseCase (Fase 3, tarea 3.1/5.1)
# ============================================================================


class TestConnectWhatsappUseCase:
    CLIENT_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"

    @pytest.mark.asyncio
    async def test_connect_approved_client(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.APPROVED,
            is_active=True,
            phone_number_id="",
            whatsapp_connected=False,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = ConnectWhatsappUseCase(mock_repo)
        inp = ConnectWhatsappInput(
            client_id=self.CLIENT_ID,
            phone_number_id="123456789",
            access_token="EAAB...secret-token",
        )

        output = await uc.execute(inp, current_role="superadmin")

        assert isinstance(output, AdminClientOutput)
        assert output.whatsapp_connected is True

        mock_repo.save.assert_awaited_once()
        saved = mock_repo.save.call_args[0][0]
        assert saved.phone_number_id == "123456789"
        assert saved.whatsapp_connected is True

        # El token en claro se persiste (cifrado) por un método separado,
        # NUNCA a través de save() del agregado de dominio.
        mock_repo.save_whatsapp_credentials.assert_awaited_once_with(
            client_id=self.CLIENT_ID,
            phone_number_id="123456789",
            access_token="EAAB...secret-token",
        )

    @pytest.mark.asyncio
    async def test_connect_not_found_raises(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = None

        uc = ConnectWhatsappUseCase(mock_repo)
        inp = ConnectWhatsappInput(
            client_id=self.CLIENT_ID, phone_number_id="123", access_token="tok"
        )

        with pytest.raises(InvalidClientError, match="not found"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.save.assert_not_awaited()
        mock_repo.save_whatsapp_credentials.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_non_superadmin_raises(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)

        uc = ConnectWhatsappUseCase(mock_repo)
        inp = ConnectWhatsappInput(
            client_id=self.CLIENT_ID, phone_number_id="123", access_token="tok"
        )

        with pytest.raises(ForbiddenError, match="Only superadmin"):
            await uc.execute(inp, current_role="client_admin")

        mock_repo.find_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_empty_phone_number_id_raises(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)

        uc = ConnectWhatsappUseCase(mock_repo)
        inp = ConnectWhatsappInput(client_id=self.CLIENT_ID, phone_number_id="  ", access_token="tok")

        with pytest.raises(InvalidClientError, match="phone_number_id"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.find_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_empty_access_token_raises(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)

        uc = ConnectWhatsappUseCase(mock_repo)
        inp = ConnectWhatsappInput(client_id=self.CLIENT_ID, phone_number_id="123", access_token=" ")

        with pytest.raises(InvalidClientError, match="access_token"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.find_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_client_not_approved_raises(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.PENDING,
            is_active=True,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = ConnectWhatsappUseCase(mock_repo)
        inp = ConnectWhatsappInput(
            client_id=self.CLIENT_ID, phone_number_id="123456789", access_token="tok"
        )

        with pytest.raises(InvalidClientError, match="approved"):
            await uc.execute(inp, current_role="superadmin")

        mock_repo.save.assert_not_awaited()
        mock_repo.save_whatsapp_credentials.assert_not_awaited()
