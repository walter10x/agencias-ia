"""Tests unitarios para el agregado Client."""

import uuid

import pytest

from app.domain.client.entity import Client
from app.domain.shared.value_objects import BusinessType, WhatsAppNumber


class TestClientCreation:
    def test_creates_with_minimum_data(self) -> None:
        client = Client(
            name="Peluquería El Buen Corte",
            business_type=BusinessType("peluqueria"),
            whatsapp_number=WhatsAppNumber("573001234567"),
        )
        assert client.name == "Peluquería El Buen Corte"
        assert str(client.business_type) == "peluqueria"
        assert str(client.whatsapp_number) == "573001234567"
        assert client.is_active is True
        assert client.id is not None

    def test_raises_on_empty_name(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            Client(name="", business_type=BusinessType("bar"))

    def test_id_is_stable_after_creation(self) -> None:
        client = Client(name="Bar Test")
        assert client.id is not None
        assert isinstance(client.id, uuid.UUID)


class TestClientBehavior:
    def test_deactivate_client(self) -> None:
        client = Client(name="Test Client", business_type=BusinessType("otro"))
        client.deactivate()
        assert client.is_active is False

    def test_reactivate_client(self) -> None:
        client = Client(name="Test Client", business_type=BusinessType("otro"))
        client.deactivate()
        client.activate()
        assert client.is_active is True

    def test_update_name(self) -> None:
        client = Client(name="Old Name", business_type=BusinessType("otro"))
        client.update_name("New Name")
        assert client.name == "New Name"

    def test_update_name_raises_on_empty(self) -> None:
        client = Client(name="Old Name", business_type=BusinessType("otro"))
        with pytest.raises(ValueError):
            client.update_name("  ")

    def test_change_whatsapp(self) -> None:
        client = Client(name="Test", business_type=BusinessType("otro"))
        new_num = WhatsAppNumber("573009876543")
        client.change_whatsapp(new_num)
        assert str(client.whatsapp_number) == "573009876543"


class TestClientEquality:
    def test_same_id_are_equal(self) -> None:
        cid = uuid.uuid4()
        a = Client(id=cid, name="A", business_type=BusinessType("otro"))
        b = Client(id=cid, name="B", business_type=BusinessType("bar"))
        assert a == b

    def test_different_id_not_equal(self) -> None:
        a = Client(name="A", business_type=BusinessType("otro"))
        b = Client(name="A", business_type=BusinessType("otro"))
        assert a != b
