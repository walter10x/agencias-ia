"""Adaptador Jwt — HS256 vía python-jose."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.application.ports import JwtPort
from app.domain.shared.errors import UnauthorizedError
from app.infrastructure.config.settings import Settings


class JoseJwtHandler(JwtPort):
    """Implementación JWT HS256 del puerto JwtPort.

    Usa python-jose con algoritmo HS256.
    El secret y tiempo de expiración se leen de Settings.
    """

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._expire_minutes = settings.jwt_expire_minutes

    def sign(self, sub: str, role: str, client_id: str | None) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": sub,
            "role": role,
            "client_id": client_id,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> dict[str, str]:
        try:
            return jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"verify_exp": True},
            )
        except JWTError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc
