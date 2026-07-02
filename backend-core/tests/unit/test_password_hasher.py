"""Tests para BcryptPasswordHasher (TDD — phase 1: RED)."""

from __future__ import annotations

import pytest

from app.domain.shared.value_objects import PasswordHash


class TestBcryptPasswordHasher:
    def test_bcrypt_hasher_imports(self) -> None:
        """RED phase — clase aún no existe."""
        from app.infrastructure.security.password_hasher import BcryptPasswordHasher

        hasher = BcryptPasswordHasher()
        assert hasher is not None

    def test_hash_and_verify_roundtrip(self) -> None:
        from app.infrastructure.security.password_hasher import BcryptPasswordHasher

        hasher = BcryptPasswordHasher()
        hashed = hasher.hash_password("S3cret!")
        assert isinstance(hashed, PasswordHash)
        assert hasher.verify("S3cret!", hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        from app.infrastructure.security.password_hasher import BcryptPasswordHasher

        hasher = BcryptPasswordHasher()
        hashed = hasher.hash_password("S3cret!")
        assert hasher.verify("Wrong!", hashed) is False

    def test_hash_does_not_leak_plain(self) -> None:
        from app.infrastructure.security.password_hasher import BcryptPasswordHasher

        hasher = BcryptPasswordHasher()
        hashed = hasher.hash_password("S3cret!")
        assert "S3cret!" not in str(hashed)
        assert str(hashed).startswith("$2")
        assert len(str(hashed)) >= 60
