"""Tests unitarios para los enums del agregado Client."""

from app.domain.client.enums import ClientRole, ClientStatus


class TestClientRole:
    def test_client_role_values(self) -> None:
        assert ClientRole.SUPERADMIN.value == "superadmin"
        assert ClientRole.CLIENT_ADMIN.value == "client_admin"
        assert ClientRole.CLIENT_USER.value == "client_user"

    def test_role_is_str_enum(self) -> None:
        assert isinstance(ClientRole.CLIENT_ADMIN, str)


class TestClientStatus:
    def test_client_status_values(self) -> None:
        assert ClientStatus.PENDING.value == "pending"
        assert ClientStatus.APPROVED.value == "approved"
        assert ClientStatus.ACTIVE.value == "active"
        assert ClientStatus.INACTIVE.value == "inactive"

    def test_status_is_str_enum(self) -> None:
        assert isinstance(ClientStatus.PENDING, str)