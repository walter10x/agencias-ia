from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from app.application.dtos import CurrentClientOutput
from app.domain.client.entity import Client
from app.domain.client.enums import ClientRole, ClientStatus
from app.domain.shared.value_objects import Email, PasswordHash
from app.infrastructure.http.auth_router import router as auth_router
from app.infrastructure.http.dependencies import (
    get_client_repo,
    get_current_client,
    get_jwt_handler,
    get_password_hasher,
)

pytestmark = pytest.mark.asyncio


def _make_app() -> FastAPI:
    _app = FastAPI()
    _app.include_router(auth_router, prefix="/api/v1/auth")
    return _app


async def _client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class FakePasswordHasher:
    def hash_password(self, plain: str) -> PasswordHash:
        return PasswordHash(f"$2b$12$H{plain}{'x' * (53 - 1 - len(plain))}")

    def verify(self, plain: str, hashed: PasswordHash) -> bool:
        return True


class FakeJwtHandler:
    def sign(self, sub: str, role: str, client_id: str | None) -> str:
        return f"token_{sub}_{role}_{client_id or 'none'}"

    def decode(self, token: str) -> dict[str, object]:
        parts = token.split("_")
        return {
            "sub": parts[1] if len(parts) > 1 else "",
            "role": parts[2] if len(parts) > 2 else "",
            "client_id": parts[3] if len(parts) > 3 and parts[3] != "none" else None,
        }


# ============================================================================
# POST /api/v1/auth/register
# ============================================================================


class TestRegisterEndpoint:
    async def test_register_201(self) -> None:
        mock_repo = AsyncMock()
        mock_repo.find_by_email.return_value = None
        mock_repo.find_by_whatsapp.return_value = None

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/register", json={
                "email": "test@example.com",
                "password": "SecurePass1",
                "business_name": "Mi Negocio",
                "whatsapp_number": "573001234567",
            })

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["status"] == "pending"
        assert data["client_id"]
        assert data["message"]

    async def test_register_409_duplicate_email(self) -> None:
        mock_repo = AsyncMock()
        mock_repo.find_by_email.return_value = AsyncMock()

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/register", json={
                "email": "dupe@example.com",
                "password": "SecurePass1",
                "business_name": "Mi Negocio",
                "whatsapp_number": "573001234567",
            })

        assert resp.status_code == status.HTTP_409_CONFLICT

    async def test_register_422_weak_password(self) -> None:
        mock_repo = AsyncMock()
        mock_repo.find_by_email.return_value = None

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/register", json={
                "email": "test@example.com",
                "password": "Ab1",
                "business_name": "Mi Negocio",
                "whatsapp_number": "573001234567",
            })

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_400_invalid_whatsapp(self) -> None:
        mock_repo = AsyncMock()
        mock_repo.find_by_email.return_value = None

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/register", json={
                "email": "test@example.com",
                "password": "SecurePass1",
                "business_name": "Mi Negocio",
                "whatsapp_number": "aaaaaaaaaa",  # 10 chars but not digits → domain error
            })

        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# POST /api/v1/auth/login
# ============================================================================


class TestLoginEndpoint:
    async def test_login_200(self) -> None:
        mock_repo = AsyncMock()
        hash_pw = FakePasswordHasher().hash_password("SecurePass1")
        mock_repo.find_by_email.return_value = Client(
            name="Test",
            email=Email("test@example.com"),
            password_hash=hash_pw,
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.ACTIVE,
            is_active=True,
        )

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()
        app.dependency_overrides[get_jwt_handler] = lambda: FakeJwtHandler()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "SecurePass1",
            })

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["client_id"]
        assert data["role"] == "client_admin"
        assert data["status"] == "active"

    async def test_login_401_invalid_credentials(self) -> None:
        mock_repo = AsyncMock()
        mock_repo.find_by_email.return_value = None

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()
        app.dependency_overrides[get_jwt_handler] = lambda: FakeJwtHandler()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/login", json={
                "email": "nobody@example.com",
                "password": "WrongPass1",
            })

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_403_pending(self) -> None:
        mock_repo = AsyncMock()
        hash_pw = FakePasswordHasher().hash_password("SecurePass1")
        mock_repo.find_by_email.return_value = Client(
            name="Pending",
            email=Email("pending@example.com"),
            password_hash=hash_pw,
            role=ClientRole.CLIENT_ADMIN,
            status=ClientStatus.PENDING,
            is_active=True,
        )

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()
        app.dependency_overrides[get_jwt_handler] = lambda: FakeJwtHandler()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/login", json={
                "email": "pending@example.com",
                "password": "SecurePass1",
            })

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    async def test_login_422_validation_error(self) -> None:
        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()
        app.dependency_overrides[get_jwt_handler] = lambda: FakeJwtHandler()

        async with await _client(app) as c:
            resp = await c.post("/api/v1/auth/login", json={"email": 123, "password": 456})

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# GET /api/v1/auth/me
# ============================================================================


class TestMeEndpoint:
    async def test_me_200(self) -> None:
        current = CurrentClientOutput(
            client_id=str(uuid.uuid4()),
            email="test@example.com",
            name="Mi Negocio",
            role="client_admin",
            status="active",
            whatsapp_number="573001234567",
            whatsapp_connected=True,
            plan="pro",
            is_active=True,
        )

        app = _make_app()
        app.dependency_overrides[get_current_client] = lambda: current

        async with await _client(app) as c:
            resp = await c.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "client_admin"
        assert data["status"] == "active"
        assert data["plan"] == "pro"
        assert data["whatsapp_connected"] is True

    async def test_me_401_no_token(self) -> None:
        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: AsyncMock()
        app.dependency_overrides[get_jwt_handler] = lambda: FakeJwtHandler()

        async with await _client(app) as c:
            resp = await c.get("/api/v1/auth/me")

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
