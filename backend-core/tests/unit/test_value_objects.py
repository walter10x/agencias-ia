"""Tests unitarios para Value Objects compartidos."""

import pytest

from app.domain.shared.errors import InvalidClientError, InvalidAgentError
from app.domain.shared.value_objects import (
    AgentId,
    BusinessType,
    ClientId,
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
