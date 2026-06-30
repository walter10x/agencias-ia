"""Integration tests for SupabaseClientRepository.

These tests hit a real Supabase instance.  They are the RED phase of TDD:
the repository does NOT exist yet, so every test will fail on import.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.client.entity import Client
from app.domain.shared.errors import InvalidClientError
from app.domain.shared.value_objects import (
    BusinessType,
    ClientId,
    WhatsAppNumber,
)
from app.infrastructure.persistence.client_repository import (  # type: ignore[import-untyped]  # noqa: E501
    SupabaseClientRepository,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ======================================================================
# Helpers
# ======================================================================

def _make_client(
    name: str = "Test Client",
    whatsapp: str = "573000000000",
    business_type: str = "otro",
    active: bool = True,
    client_id: UUID | None = None,
) -> Client:
    """Shorthand factory for creating Client entities in tests."""
    return Client(
        id=client_id or uuid4(),
        name=name,
        business_type=BusinessType(business_type),
        whatsapp_number=WhatsAppNumber(whatsapp),
        is_active=active,
    )


# ======================================================================
# save()
# ======================================================================

class TestSaveNewClient:
    """RF-01: INSERT a brand-new client."""

    async def test_save_new_client(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """Saving a new client persists it, and find_by_id retrieves it."""
        client = _make_client(name="Nuevo Cliente", whatsapp="573001234001")

        await client_repo.save(client)

        found = await client_repo.find_by_id(ClientId(value=client.id))
        assert found is not None
        assert found.id == client.id
        assert found.name == "Nuevo Cliente"
        assert str(found.whatsapp_number) == "573001234001"


class TestSaveExistingClientUpdates:
    """RF-01: UPDATE an existing client (UPSERT semantics)."""

    async def test_save_existing_client_updates(
        self,
        client_repo: SupabaseClientRepository,
        sample_client: Client,
    ) -> None:
        """Saving a client that already exists updates its fields."""
        # First insert
        await client_repo.save(sample_client)

        # Modify in-memory entity
        sample_client.update_name("Nombre Modificado")
        sample_client.deactivate()

        # Second save → UPDATE
        await client_repo.save(sample_client)

        found = await client_repo.find_by_id(ClientId(value=sample_client.id))
        assert found is not None
        assert found.name == "Nombre Modificado"
        assert found.is_active is False


class TestSaveDuplicateWhatsappRaises:
    """EC-01 / RF-01: uniqueness violation on whatsapp_number."""

    async def test_save_duplicate_whatsapp_raises(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """Saving two clients with the same WhatsApp raises InvalidClientError."""
        client_a = _make_client(
            name="Cliente A",
            whatsapp="573001234005",
        )
        client_b = _make_client(
            name="Cliente B",
            whatsapp="573001234005",  # same number, different id
        )

        await client_repo.save(client_a)

        with pytest.raises(InvalidClientError, match="WhatsApp"):
            await client_repo.save(client_b)


# ======================================================================
# find_by_id()
# ======================================================================

class TestFindByIdReturnsClient:
    """RF-02: retrieve an existing client by its ClientId."""

    async def test_find_by_id_returns_client(
        self,
        client_repo: SupabaseClientRepository,
        sample_client: Client,
    ) -> None:
        """find_by_id returns the matching Client entity."""
        await client_repo.save(sample_client)

        found = await client_repo.find_by_id(ClientId(value=sample_client.id))

        assert found is not None
        assert found.id == sample_client.id
        assert found.name == sample_client.name
        assert str(found.business_type) == str(sample_client.business_type)
        assert str(found.whatsapp_number) == str(sample_client.whatsapp_number)
        assert found.is_active == sample_client.is_active


class TestFindByIdReturnsNoneForMissing:
    """EC-03: valid but non-existent UUID → None."""

    async def test_find_by_id_returns_none_for_missing(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """find_by_id with a random, unpersisted ClientId returns None."""
        random_id = ClientId.generate()
        found = await client_repo.find_by_id(random_id)
        assert found is None


# ======================================================================
# find_by_whatsapp()
# ======================================================================

class TestFindByWhatsappFound:
    """RF-03: search by WhatsApp number — found case."""

    async def test_find_by_whatsapp_found(
        self,
        client_repo: SupabaseClientRepository,
        sample_client: Client,
    ) -> None:
        """find_by_whatsapp returns the client when the number exists."""
        await client_repo.save(sample_client)

        found = await client_repo.find_by_whatsapp(
            str(sample_client.whatsapp_number)
        )

        assert found is not None
        assert found.id == sample_client.id


class TestFindByWhatsappNotFound:
    """RF-03: search by WhatsApp number — not-found case."""

    async def test_find_by_whatsapp_not_found(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """find_by_whatsapp with an unregistered number returns None."""
        found = await client_repo.find_by_whatsapp("573009999999")
        assert found is None


class TestFindByWhatsappInvalidNumberRaises:
    """EC-02 variant: invalid WhatsApp format → InvalidClientError."""

    async def test_find_by_whatsapp_invalid_number_raises(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """find_by_whatsapp with a non-numeric string raises InvalidClientError."""
        with pytest.raises(InvalidClientError):
            await client_repo.find_by_whatsapp("not-a-number")


# ======================================================================
# list_active()
# ======================================================================

class TestListActiveReturnsOnlyActive:
    """RF-04: list_active filters out inactive clients."""

    async def test_list_active_returns_only_active(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """Only clients with is_active=True appear in list_active."""
        active = _make_client(
            name="Activo",
            whatsapp="573001234010",
            active=True,
        )
        inactive = _make_client(
            name="Inactivo",
            whatsapp="573001234011",
            active=False,
        )

        await client_repo.save(active)
        await client_repo.save(inactive)

        result = await client_repo.list_active(limit=50)

        ids = {c.id for c in result}
        assert active.id in ids
        assert inactive.id not in ids
        assert all(c.is_active for c in result)


class TestListActivePagination:
    """RF-04: limit and offset pagination works correctly."""

    async def test_list_active_pagination(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """list_active with limit/offset returns the correct slice."""
        # Save 3 active clients with different WhatsApp numbers
        clients = [
            _make_client(
                name=f"Pag Client {i}",
                whatsapp=f"57300123401{i}",
                active=True,
            )
            for i in range(3)
        ]
        for c in clients:
            await client_repo.save(c)

        # Page 1: offset=0, limit=2 → first two (most recently created)
        page1 = await client_repo.list_active(limit=2, offset=0)
        assert len(page1) == 2

        # Page 2: offset=2, limit=2 → remaining one
        page2 = await client_repo.list_active(limit=2, offset=2)
        assert len(page2) == 1

        # No overlap
        page1_ids = {c.id for c in page1}
        page2_ids = {c.id for c in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestListActiveEmpty:
    """EC-05: no active clients → empty list."""

    async def test_list_active_empty(
        self,
        client_repo: SupabaseClientRepository,
    ) -> None:
        """list_active returns an empty list when there are no clients."""
        result = await client_repo.list_active(limit=10)
        assert result == []
        assert isinstance(result, list)
