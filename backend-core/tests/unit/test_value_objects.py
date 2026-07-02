"""Tests unitarios para Value Objects compartidos."""

import pytest

from app.domain.shared.errors import InvalidClientError, InvalidAgentError
from app.domain.shared.value_objects import (
    AgentId,
    BusinessType,
    ClientId,
    Email,
    PasswordHash,
    WhatsAppNumber,
)


class TestClientId:
    def test_generates_valid_uuid(self) -> None:
        cid = ClientId.generate()
        assert len(str(cid)) == 36

    def test_from_string_valid_uuid(self) -> None:
        cid = ClientId.from_string("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert str(cid) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(InvalidClientError):
            ClientId.from_string("not-a-uuid")


class TestAgentId:
    def test_generates_valid_uuid(self) -> None:
        aid = AgentId.generate()
        assert len(str(aid)) == 36

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(InvalidAgentError):
            AgentId.from_string("invalid")


class TestWhatsAppNumber:
    def test_strips_formatting(self) -> None:
        num = WhatsAppNumber("+57 300-123-4567")
        assert str(num) == "573001234567"

    def test_raises_on_invalid(self) -> None:
        with pytest.raises(ValueError):
            WhatsAppNumber("abc")

    def test_raises_on_too_short(self) -> None:
        with pytest.raises(ValueError):
            WhatsAppNumber("12345")


class TestBusinessType:
    def test_valid_types(self) -> None:
        for t in ["peluqueria", "bar", "restaurante", "contador"]:
            bt = BusinessType(t)
            assert str(bt) == t

    def test_normalizes_case(self) -> None:
        bt = BusinessType("PELUQUERIA")
        assert str(bt) == "peluqueria"

    def test_raises_on_invalid(self) -> None:
        with pytest.raises(ValueError):
            BusinessType("astronauta")


class TestEmail:
    def test_email_valid_normalizes_lowercase(self) -> None:
        email = Email("User@Example.COM")
        assert str(email) == "user@example.com"
        assert email.value == "user@example.com"

    def test_email_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError):
            Email("no-arroba")
        with pytest.raises(ValueError):
            Email("a@b")
        # uno válido no debe lanzar
        assert str(Email("a@b.co")) == "a@b.co"

    def test_email_too_short_raises(self) -> None:
        # dominio muy corto (TLD < 2 chars o sin punto)
        with pytest.raises(ValueError):
            Email("a@b")

    def test_email_strips_whitespace(self) -> None:
        assert str(Email("  user@example.com  ")) == "user@example.com"

    def test_email_too_long_raises(self) -> None:
        # 254 es el máx RFC 5321
        with pytest.raises(ValueError):
            Email("a" * 250 + "@x.co")


class TestPasswordHash:
    def test_password_hash_valid_bcrypt(self) -> None:
        # hash bcrypt válido de 60 chars con prefijo $2a$
        raw = "$2a$12$abcdefghijklmnopqrstuv123456789012345678901234567890123456789012"
        ph = PasswordHash(raw)
        assert str(ph) == raw
        assert ph.value == raw

    def test_password_hash_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError):
            PasswordHash("plain")
        with pytest.raises(ValueError):
            PasswordHash("$2a$10$short")

    def test_password_hash_value_is_str(self) -> None:
        raw = "$2b$12$abcdefghijklmnopqrstuv123456789012345678901234567890123456789012"
        assert str(PasswordHash(raw)) == raw

    def test_password_hash_rejects_wrong_length(self) -> None:
        # prefijo correcto pero longitud incorrecta
        with pytest.raises(ValueError):
            PasswordHash("$2a$12$only40chars______________________________")

    def test_password_hash_rejects_unknown_scheme(self) -> None:
        with pytest.raises(ValueError):
            PasswordHash("$3$12$abcdefghijklmnopqrstuv123456789012345678901234567890123456789012")
