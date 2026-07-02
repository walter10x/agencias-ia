"""Tests para JoseJwtHandler (TDD — phase 1: RED)."""

from __future__ import annotations

import time

import pytest

from app.domain.shared.errors import UnauthorizedError
from app.infrastructure.config.settings import Settings


class TestJoseJwtHandler:
    def test_jwt_handler_imports(self) -> None:
        from app.infrastructure.security.jwt_handler import JoseJwtHandler

        handler = JoseJwtHandler(Settings(jwt_secret="test-secret"))
        assert handler is not None

    def test_sign_and_decode_roundtrip(self) -> None:
        from app.infrastructure.security.jwt_handler import JoseJwtHandler

        handler = JoseJwtHandler(Settings(jwt_secret="test-secret", jwt_expire_minutes=60))
        token = handler.sign(sub="client-uuid-1", role="client_admin", client_id="client-uuid-1")
        claims = handler.decode(token)
        assert claims["sub"] == "client-uuid-1"
        assert claims["role"] == "client_admin"
        assert claims["client_id"] == "client-uuid-1"
        assert "exp" in claims
        assert "iat" in claims

    def test_decode_expired_token_raises(self) -> None:
        from app.infrastructure.security.jwt_handler import JoseJwtHandler

        handler = JoseJwtHandler(Settings(jwt_secret="test-secret", jwt_expire_minutes=-5))
        token = handler.sign(sub="uuid-x", role="client_admin", client_id="uuid-x")
        with pytest.raises(UnauthorizedError):
            handler.decode(token)

    def test_decode_invalid_token_raises(self) -> None:
        from app.infrastructure.security.jwt_handler import JoseJwtHandler

        handler = JoseJwtHandler(Settings(jwt_secret="test-secret"))
        with pytest.raises(UnauthorizedError):
            handler.decode("garbage-token")

    def test_sign_with_different_secret_fails(self) -> None:
        from app.infrastructure.security.jwt_handler import JoseJwtHandler

        signer = JoseJwtHandler(Settings(jwt_secret="secret-a"))
        verifier = JoseJwtHandler(Settings(jwt_secret="secret-b"))
        token = signer.sign(sub="uuid", role="superadmin", client_id="uuid")
        with pytest.raises(UnauthorizedError):
            verifier.decode(token)
