"""Unit tests for SupabaseClientRepository — fully mocked, no real Supabase needed."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.domain.client.entity import Client
from app.domain.shared.errors import InvalidClientError
from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber
from app.infrastructure.persistence.client_repository import SupabaseClientRepository


def _make_mock_chain() -> MagicMock:
    """Create a mock that returns itself for all chained method calls."""
    chain = MagicMock()
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.offset.return_value = chain
    chain.execute.return_value = chain
    return chain


class _FakeCipher:
    """Fake de CredentialsCipherPort — reversible y determinista para tests."""

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return f"enc:{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        return ciphertext.removeprefix("enc:")


def _make_row(
    id_: str,
    name: str = "Test",
    business_type: str = "otro",
    whatsapp: str = "573000000000",
    is_active: bool = True,
) -> dict:
    return {
        "id": id_,
        "name": name,
        "business_type": business_type,
        "whatsapp_number": whatsapp,
        "is_active": is_active,
        "created_at": "2026-06-07T00:00:00+00:00",
        "updated_at": "2026-06-07T00:00:00+00:00",
    }


@pytest.fixture
def mock_db() -> MagicMock:
    """Supabase client mock with chaining support."""
    db = MagicMock()
    table = MagicMock()
    chain = _make_mock_chain()
    table.select.return_value = chain
    table.upsert.return_value = chain
    table.update.return_value = chain
    db.table.return_value = table
    db._chain = chain  # expose chain for test assertions
    db._table = table
    return db


@pytest.fixture
def repo(mock_db: MagicMock) -> SupabaseClientRepository:
    return SupabaseClientRepository(mock_db, cipher=_FakeCipher())


@pytest.fixture
def client() -> Client:
    return Client(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Test Peluqueria",
        business_type=BusinessType("peluqueria"),
        whatsapp_number=WhatsAppNumber("573001234567"),
        is_active=True,
    )


# ======================================================================
# save()
# ======================================================================

@pytest.mark.asyncio
async def test_save_new_client(repo: SupabaseClientRepository, mock_db: MagicMock, client: Client) -> None:
    await repo.save(client)
    mock_db._table.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_save_triggers_upsert(repo: SupabaseClientRepository, mock_db: MagicMock, client: Client) -> None:
    await repo.save(client)
    # Verify upsert called on the correct table
    mock_db.table.assert_called_with("clients")


# ======================================================================
# find_by_id()
# ======================================================================

@pytest.mark.asyncio
async def test_find_by_id_returns_client(repo: SupabaseClientRepository, mock_db: MagicMock, client: Client) -> None:
    mock_db._chain.data = [_make_row(str(client.id), name=client.name)]

    found = await repo.find_by_id(ClientId(value=client.id))

    assert found is not None
    assert found.id == client.id
    assert found.name == client.name
    mock_db.table.assert_called_with("clients")


@pytest.mark.asyncio
async def test_find_by_id_returns_none_for_missing(repo: SupabaseClientRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = []
    found = await repo.find_by_id(ClientId.generate())
    assert found is None


# ======================================================================
# find_by_whatsapp()
# ======================================================================

@pytest.mark.asyncio
async def test_find_by_whatsapp_found(repo: SupabaseClientRepository, mock_db: MagicMock, client: Client) -> None:
    mock_db._chain.data = [_make_row(str(client.id), whatsapp="573001234567")]

    found = await repo.find_by_whatsapp("573001234567")

    assert found is not None
    assert found.id == client.id


@pytest.mark.asyncio
async def test_find_by_whatsapp_not_found(repo: SupabaseClientRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = []
    found = await repo.find_by_whatsapp("573009999999")
    assert found is None


@pytest.mark.asyncio
async def test_find_by_whatsapp_invalid_raises(repo: SupabaseClientRepository) -> None:
    with pytest.raises(InvalidClientError):
        await repo.find_by_whatsapp("not-a-number")


# ======================================================================
# list_active()
# ======================================================================

@pytest.mark.asyncio
async def test_list_active_returns_list(repo: SupabaseClientRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = [
        _make_row(str(uuid4()), name="Active 1", is_active=True),
    ]

    result = await repo.list_active(limit=10)

    assert len(result) == 1
    assert result[0].is_active


@pytest.mark.asyncio
async def test_list_active_empty(repo: SupabaseClientRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = []
    result = await repo.list_active()
    assert result == []


@pytest.mark.asyncio
async def test_list_active_limit_zero_raises(repo: SupabaseClientRepository) -> None:
    with pytest.raises(InvalidClientError):
        await repo.list_active(limit=0)


@pytest.mark.asyncio
async def test_list_active_offset_negative_raises(repo: SupabaseClientRepository) -> None:
    with pytest.raises(InvalidClientError):
        await repo.list_active(offset=-1)


# ======================================================================
# Error mapping
# ======================================================================

@pytest.mark.asyncio
async def test_save_uniqueness_error_maps_to_invalid_client(repo: SupabaseClientRepository, mock_db: MagicMock, client: Client) -> None:
    """Simulate PostgreSQL 23505 unique_violation."""
    error = Exception("duplicate key value violates unique constraint")
    error.code = "23505"  # type: ignore[attr-defined]
    mock_db._table.upsert.side_effect = error

    with pytest.raises(InvalidClientError, match="WhatsApp"):
        await repo.save(client)


# ======================================================================
# find_by_phone_number_id() — Fase 3, routing multi-tenant del webhook
# ======================================================================


@pytest.mark.asyncio
async def test_find_by_phone_number_id_found(repo: SupabaseClientRepository, mock_db: MagicMock, client: Client) -> None:
    row = _make_row(str(client.id))
    row["phone_number_id"] = "123456789"
    mock_db._chain.data = [row]

    found = await repo.find_by_phone_number_id("123456789")

    assert found is not None
    assert found.id == client.id


@pytest.mark.asyncio
async def test_find_by_phone_number_id_not_found(repo: SupabaseClientRepository, mock_db: MagicMock) -> None:
    mock_db._chain.data = []
    found = await repo.find_by_phone_number_id("does-not-exist")
    assert found is None


@pytest.mark.asyncio
async def test_find_by_phone_number_id_empty_string_returns_none_without_query(
    repo: SupabaseClientRepository, mock_db: MagicMock
) -> None:
    found = await repo.find_by_phone_number_id("")
    assert found is None
    mock_db.table.assert_not_called()


# ======================================================================
# get_whatsapp_credentials() — Fase 3, tarea 3.1
# ======================================================================


@pytest.mark.asyncio
async def test_get_whatsapp_credentials_returns_decrypted_token(
    repo: SupabaseClientRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.data = [
        {
            "phone_number_id": "999888777",
            "whatsapp_access_token_encrypted": "enc:real-token-value",
        }
    ]

    creds = await repo.get_whatsapp_credentials("some-client-id")

    assert creds.has_credentials is True
    assert creds.phone_number_id == "999888777"
    assert creds.access_token == "real-token-value"


@pytest.mark.asyncio
async def test_get_whatsapp_credentials_missing_client_returns_empty(
    repo: SupabaseClientRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.data = []

    creds = await repo.get_whatsapp_credentials("unknown-client-id")

    assert creds.has_credentials is False
    assert creds.phone_number_id == ""
    assert creds.access_token == ""


@pytest.mark.asyncio
async def test_get_whatsapp_credentials_empty_token_column_returns_no_credentials(
    repo: SupabaseClientRepository, mock_db: MagicMock
) -> None:
    mock_db._chain.data = [
        {"phone_number_id": "999888777", "whatsapp_access_token_encrypted": ""}
    ]

    creds = await repo.get_whatsapp_credentials("some-client-id")

    assert creds.has_credentials is False
    assert creds.phone_number_id == "999888777"
    assert creds.access_token == ""


# ======================================================================
# save_whatsapp_credentials() — Fase 3, tarea 3.1
# ======================================================================


@pytest.mark.asyncio
async def test_save_whatsapp_credentials_encrypts_before_persisting(
    repo: SupabaseClientRepository, mock_db: MagicMock
) -> None:
    await repo.save_whatsapp_credentials(
        client_id="some-client-id",
        phone_number_id="111222333",
        access_token="plain-secret-token",
    )

    mock_db._table.update.assert_called_once()
    payload = mock_db._table.update.call_args[0][0]
    assert payload["phone_number_id"] == "111222333"
    assert payload["whatsapp_access_token_encrypted"] == "enc:plain-secret-token"
    assert payload["whatsapp_connected"] is True
