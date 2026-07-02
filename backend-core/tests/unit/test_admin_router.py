from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from app.application.dtos import CurrentClientOutput
from app.domain.client.entity import Client
from app.domain.client.enums import ClientRole, ClientStatus
from app.domain.shared.value_objects import Email, PasswordHash, WhatsAppNumber
from app.infrastructure.http.client_router import router as client_router
from app.infrastructure.http.dependencies import (
    get_client_repo,
    get_current_client,
    require_superadmin,
)

pytestmark = pytest.mark.asyncio

_VALID_FAKE_HASH = "$2b$12$" + "a" * 53


def _make_app() -> FastAPI:
    _app = FastAPI()
    _app.include_router(client_router, prefix="/api/v1/clients")
    return _app


async def _client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _make_admin_client() -> Client:
    client = Client(
        name="Test Client",
        email=Email("test@example.com"),
        password_hash=PasswordHash(_VALID_FAKE_HASH),
        role=ClientRole.CLIENT_ADMIN,
        status=ClientStatus.ACTIVE,
        is_active=True,
        whatsapp_number=WhatsAppNumber("573001234567"),
        plan="free",
    )
    object.__setattr__(client, "id", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    return client


# ============================================================================
# POST /api/v1/clients/{id}/approve
# ============================================================================


class TestApproveEndpoint:
    async def test_approve_200(self) -> None:
        client = _make_admin_client()
        object.__setattr__(client, "status", ClientStatus.PENDING)

        mock_repo = AsyncMock()
        mock_repo.find_by_id.return_value = client

        current = CurrentClientOutput(
            client_id="admin-1111",
            email="walter@admin.com",
            name="Walter",
            role="superadmin",
            status="active",
            whatsapp_number="0000000000",
            whatsapp_connected=False,
            plan="enterprise",
            is_active=True,
        )

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_current_client] = lambda: current
        app.dependency_overrides[require_superadmin] = lambda: current

        async with await _client(app) as c:
            resp = await c.post("/api/v1/clients/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/approve")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "approved"
        assert data["email"] == "test@example.com"

    async def test_approve_403_non_superadmin(self) -> None:
        async def _forbidden() -> AdminClientOutput:
            raise HTTPException(status_code=403, detail="Superadmin access required")

        app = _make_app()
        app.dependency_overrides[require_superadmin] = _forbidden

        async with await _client(app) as c:
            resp = await c.post("/api/v1/clients/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/approve")

        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# POST /api/v1/clients/{id}/reject
# ============================================================================


class TestRejectEndpoint:
    async def test_reject_200(self) -> None:
        client = _make_admin_client()
        object.__setattr__(client, "status", ClientStatus.PENDING)

        mock_repo = AsyncMock()
        mock_repo.find_by_id.return_value = client

        current = CurrentClientOutput(
            client_id="admin-1111",
            email="walter@admin.com",
            name="Walter",
            role="superadmin",
            status="active",
            whatsapp_number="0000000000",
            whatsapp_connected=False,
            plan="enterprise",
            is_active=True,
        )

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_current_client] = lambda: current
        app.dependency_overrides[require_superadmin] = lambda: current

        async with await _client(app) as c:
            resp = await c.post("/api/v1/clients/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/reject")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "inactive"
        assert data["is_active"] is False


# ============================================================================
# POST /api/v1/clients/{id}/disconnect-whatsapp
# ============================================================================


class TestDisconnectWhatsappEndpoint:
    async def test_disconnect_200(self) -> None:
        client = _make_admin_client()
        client.phone_number_id = "123456789"
        client.whatsapp_connected = True

        mock_repo = AsyncMock()
        mock_repo.find_by_id.return_value = client

        current = CurrentClientOutput(
            client_id="admin-1111",
            email="walter@admin.com",
            name="Walter",
            role="superadmin",
            status="active",
            whatsapp_number="0000000000",
            whatsapp_connected=False,
            plan="enterprise",
            is_active=True,
        )

        app = _make_app()
        app.dependency_overrides[get_client_repo] = lambda: mock_repo
        app.dependency_overrides[get_current_client] = lambda: current
        app.dependency_overrides[require_superadmin] = lambda: current

        async with await _client(app) as c:
            resp = await c.post(
                "/api/v1/clients/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/disconnect-whatsapp"
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["whatsapp_connected"] is False
