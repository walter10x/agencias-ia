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
    db.table.return_value = table
    db._chain = chain  # expose chain for test assertions
    db._table = table
    return db


@pytest.fixture
def repo(mock_db: MagicMock) -> SupabaseClientRepository:
    return SupabaseClientRepository(mock_db)


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
