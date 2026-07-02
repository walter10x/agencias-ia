"""Adaptador PasswordHasher — bcrypt vía passlib."""

from __future__ import annotations

from passlib.context import CryptContext

from app.application.ports import PasswordHasherPort
from app.domain.shared.value_objects import PasswordHash


class BcryptPasswordHasher(PasswordHasherPort):
    """Implementación bcrypt del puerto PasswordHasherPort.

    Usa passlib CryptContext con scheme bcrypt y deprecated="auto".
    Los métodos son síncronos; deben envolverse en asyncio.to_thread
    si se llaman desde FastAPI async para no bloquear el event loop.
    """

    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, plain: str) -> PasswordHash:
        return PasswordHash(self._ctx.hash(plain))

    def verify(self, plain: str, hashed: PasswordHash) -> bool:
        return self._ctx.verify(plain, hashed.value)
