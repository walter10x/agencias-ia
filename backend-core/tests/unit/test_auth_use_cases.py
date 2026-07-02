from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.auth.login_client import LoginClientUseCase
from app.application.auth.register_client import RegisterClientUseCase
from app.application.auth.get_current_client import GetCurrentClientUseCase
from app.application.dtos import (
    CurrentClientOutput,
    LoginClientInput,
    LoginClientOutput,
    RegisterClientInput,
    RegisterClientOutput,
)

from app.domain.client.entity import Client
from app.domain.client.enums import ClientRole, ClientStatus
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import (
    AuthError,
    ClientNotApprovedError,
    EmailAlreadyRegisteredError,
    InvalidClientError,
    InvalidCredentialsError,
    WeakPasswordError,
)
from app.domain.shared.value_objects import (
    BusinessType,
    Email,
    PasswordHash,
    WhatsAppNumber,
)


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
# FAKES for ports
# ============================================================================


_BCRYPT_SUFFIX = "x" * 53
_VALID_FAKE_HASH = "$2b$12$" + "a" * 53  # 60-char valid bcrypt string


class FakePasswordHasher:
    def __init__(self) -> None:
        self._hashes: dict[str, PasswordHash] = {}
        self._force_verify: bool | None = None

    def set_verify_result(self, result: bool) -> None:
        self._force_verify = result

    def hash_password(self, plain: str) -> PasswordHash:
        h = PasswordHash(f"$2b$12$H{plain}{'x' * (53 - 1 - len(plain))}")
        self._hashes[plain] = h
        return h

    def verify(self, plain: str, hashed: PasswordHash) -> bool:
        if self._force_verify is not None:
            return self._force_verify
        stored = self._hashes.get(plain)
        return stored is not None and stored == hashed


class FakeJwtHandler:
    def __init__(self) -> None:
        self.signed: list[dict[str, object]] = []

    def sign(self, sub: str, role: str, client_id: str | None) -> str:
        self.signed.append({"sub": sub, "role": role, "client_id": client_id})
        return f"token_{sub}_{role}_{client_id or 'none'}"

    def decode(self, token: str) -> dict[str, object]:
        parts = token.split("_")
        return {
            "sub": parts[1] if len(parts) > 1 else "",
            "role": parts[2] if len(parts) > 2 else "",
            "client_id": parts[3] if len(parts) > 3 and parts[3] != "none" else None,
        }


# ============================================================================
# RegisterClientUseCase
# ============================================================================


class TestRegisterClientUseCase:
    CLIENT_ID = "11111111-1111-1111-1111-111111111111"

    @pytest.mark.asyncio
    async def test_register_success(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = None
        mock_repo.find_by_whatsapp.return_value = None
        hasher = FakePasswordHasher()

        uc = RegisterClientUseCase(mock_repo, hasher)

        saved: list[Client] = []

        async def _save(client: Client) -> None:
            saved.append(client)
            object.__setattr__(client, "id", uuid.UUID(self.CLIENT_ID))

        mock_repo.save.side_effect = _save

        inp = RegisterClientInput(
            email="test@example.com",
            password="SecurePass1",
            business_name="Mi Negocio",
            whatsapp_number="573001234567",
        )

        output = await uc.execute(inp)

        assert isinstance(output, RegisterClientOutput)
        assert output.client_id == self.CLIENT_ID
        assert output.email == "test@example.com"
        assert output.status == "pending"
        assert "aprobación" in output.message.lower() or "pending" in output.status

        mock_repo.find_by_email.assert_awaited()
        mock_repo.find_by_whatsapp.assert_awaited()
        mock_repo.save.assert_awaited_once()

        assert len(saved) == 1
        assert saved[0].name == "Mi Negocio"
        assert saved[0].email is not None
        assert str(saved[0].email) == "test@example.com"
        assert saved[0].role == ClientRole.CLIENT_ADMIN
        assert saved[0].status == ClientStatus.PENDING

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self) -> None:
        existing = _make_client(
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = existing
        hasher = FakePasswordHasher()

        uc = RegisterClientUseCase(mock_repo, hasher)
        inp = RegisterClientInput(
            email="test@example.com",
            password="SecurePass1",
            business_name="Mi Negocio",
            whatsapp_number="573001234567",
        )

        with pytest.raises(EmailAlreadyRegisteredError, match="already registered"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_register_weak_password(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        hasher = FakePasswordHasher()

        uc = RegisterClientUseCase(mock_repo, hasher)
        inp = RegisterClientInput(
            email="test@example.com",
            password="Ab1",
            business_name="Mi Negocio",
            whatsapp_number="573001234567",
        )

        with pytest.raises(WeakPasswordError, match="at least 8 characters"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_register_invalid_email_format(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        hasher = FakePasswordHasher()

        uc = RegisterClientUseCase(mock_repo, hasher)
        inp = RegisterClientInput(
            email="not-an-email",
            password="SecurePass1",
            business_name="Mi Negocio",
            whatsapp_number="573001234567",
        )

        with pytest.raises(InvalidClientError, match="Invalid email"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_register_duplicate_whatsapp(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = None
        mock_repo.find_by_whatsapp.return_value = _make_client()
        hasher = FakePasswordHasher()

        uc = RegisterClientUseCase(mock_repo, hasher)
        inp = RegisterClientInput(
            email="test@example.com",
            password="SecurePass1",
            business_name="Mi Negocio",
            whatsapp_number="573001234567",
        )

        with pytest.raises(InvalidClientError, match="WhatsApp number already registered"):
            await uc.execute(inp)

        mock_repo.save.assert_not_awaited()


# ============================================================================
# LoginClientUseCase
# ============================================================================


class TestLoginClientUseCase:
    CLIENT_ID = "22222222-2222-2222-2222-222222222222"

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            status=ClientStatus.ACTIVE,
            is_active=True,
            role=ClientRole.CLIENT_ADMIN,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = client
        hasher = FakePasswordHasher()
        hasher.set_verify_result(True)
        jwt = FakeJwtHandler()

        uc = LoginClientUseCase(mock_repo, hasher, jwt)
        inp = LoginClientInput(email="test@example.com", password="SecurePass1")

        output = await uc.execute(inp)

        assert isinstance(output, LoginClientOutput)
        assert output.access_token.startswith("token_")
        assert output.client_id == self.CLIENT_ID
        assert output.role == "client_admin"
        assert output.status == "active"

        assert len(jwt.signed) == 1
        assert jwt.signed[0]["sub"] == "test@example.com"
        assert jwt.signed[0]["role"] == "client_admin"
        assert jwt.signed[0]["client_id"] == self.CLIENT_ID

    @pytest.mark.asyncio
    async def test_login_email_not_found(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = None
        hasher = FakePasswordHasher()
        jwt = FakeJwtHandler()

        uc = LoginClientUseCase(mock_repo, hasher, jwt)
        inp = LoginClientInput(email="notfound@example.com", password="SecurePass1")

        with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            status=ClientStatus.ACTIVE,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = client
        hasher = FakePasswordHasher()
        hasher.set_verify_result(False)
        jwt = FakeJwtHandler()

        uc = LoginClientUseCase(mock_repo, hasher, jwt)
        inp = LoginClientInput(email="test@example.com", password="WrongPass1")

        with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_login_pending_client(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("pending@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            status=ClientStatus.PENDING,
            is_active=True,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = client
        hasher = FakePasswordHasher()
        hasher.set_verify_result(True)
        jwt = FakeJwtHandler()

        uc = LoginClientUseCase(mock_repo, hasher, jwt)
        inp = LoginClientInput(email="pending@example.com", password="SecurePass1")

        with pytest.raises(ClientNotApprovedError, match="pending"):
            await uc.execute(inp)

    @pytest.mark.asyncio
    async def test_login_inactive_client(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            email=Email("inactive@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            status=ClientStatus.INACTIVE,
            is_active=False,
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_email.return_value = client
        hasher = FakePasswordHasher()
        hasher.set_verify_result(True)
        jwt = FakeJwtHandler()

        uc = LoginClientUseCase(mock_repo, hasher, jwt)
        inp = LoginClientInput(email="inactive@example.com", password="SecurePass1")

        with pytest.raises(AuthError, match="inactive"):
            await uc.execute(inp)


# ============================================================================
# GetCurrentClientUseCase
# ============================================================================


class TestGetCurrentClientUseCase:
    CLIENT_ID = "33333333-3333-3333-3333-333333333333"

    @pytest.mark.asyncio
    async def test_get_current_client_success(self) -> None:
        client = _make_client(
            id=uuid.UUID(self.CLIENT_ID),
            name="Mi Negocio",
            email=Email("test@example.com"),
            password_hash=PasswordHash(_VALID_FAKE_HASH),
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.ACTIVE,
            is_active=True,
            whatsapp_connected=True,
            plan="pro",
        )
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = client

        uc = GetCurrentClientUseCase(mock_repo)
        output = await uc.execute(client_id=self.CLIENT_ID)

        assert isinstance(output, CurrentClientOutput)
        assert output.client_id == self.CLIENT_ID
        assert output.email == "test@example.com"
        assert output.name == "Mi Negocio"
        assert output.role == "client_admin"
        assert output.status == "active"
        assert output.whatsapp_number == "573001234567"
        assert output.whatsapp_connected is True
        assert output.plan == "pro"
        assert output.is_active is True

    @pytest.mark.asyncio
    async def test_get_current_client_not_found(self) -> None:
        mock_repo = AsyncMock(spec=ClientRepository)
        mock_repo.find_by_id.return_value = None

        uc = GetCurrentClientUseCase(mock_repo)

        with pytest.raises(AuthError, match="Client not found"):
            await uc.execute(client_id=self.CLIENT_ID)
