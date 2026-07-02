"""Tests unitarios para el agregado Client."""

import uuid

import pytest

from app.domain.client.entity import Client
from app.domain.client.enums import ClientRole, ClientStatus
from app.domain.shared.errors import InvalidClientError
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


class TestClientAuthDomain:
    def test_client_approve_changes_status_pending_to_approved(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        client.approve()
        assert client.status == ClientStatus.APPROVED

    def test_client_approve_when_already_approved_raises(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        client.approve()
        with pytest.raises(InvalidClientError):
            client.approve()

    def test_client_reject_changes_status_pending_to_inactive(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        client.reject()
        assert client.status == ClientStatus.INACTIVE
        assert client.is_active is False

    def test_client_reject_when_not_pending_raises(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        client.approve()
        with pytest.raises(InvalidClientError):
            client.reject()

    def test_client_connect_whatsapp_when_approved_sets_phone_number_id(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        client.approve()
        client.connect_whatsapp("phid_123")
        assert client.phone_number_id == "phid_123"
        assert client.whatsapp_connected is True

    def test_client_connect_whatsapp_when_pending_raises(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        with pytest.raises(InvalidClientError):
            client.connect_whatsapp("x")

    def test_client_disconnect_whatsapp_clears_phone_number_id(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        client.approve()
        client.connect_whatsapp("phid_abc")
        client.disconnect_whatsapp()
        assert client.phone_number_id == ""
        assert client.whatsapp_connected is False

    def test_client_can_login_when_approved_or_active_true(self) -> None:
        c1 = Client(name="C", business_type=BusinessType("otro"))
        c1.approve()
        assert c1.can_login() is True

        c2 = Client(name="C2", business_type=BusinessType("otro"))
        c2.approve()
        c2.status = ClientStatus.ACTIVE
        assert c2.can_login() is True

    def test_client_cannot_login_when_pending(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        assert client.can_login() is False

    def test_client_cannot_login_when_inactive(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        client.reject()
        assert client.can_login() is False

    def test_client_default_role_is_client_admin(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        assert client.role == ClientRole.CLIENT_ADMIN

    def test_client_default_status_is_pending(self) -> None:
        client = Client(name="C", business_type=BusinessType("otro"))
        assert client.status == ClientStatus.PENDING
