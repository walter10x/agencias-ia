"""Puerto PasswordHasher — abstracción para hashing de contraseñas.

La capa de aplicación define este puerto. La infraestructura provee
el adaptador concreto BcryptPasswordHasher. El dominio NO conoce bcrypt.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.shared.value_objects import PasswordHash


class PasswordHasherPort(Protocol):
    """Interfaz para hashing/verificación de contraseñas."""

    def hash_password(self, plain: str) -> PasswordHash:
        """Genera un hash bcrypt a partir de una contraseña plain text."""
        ...

    def verify(self, plain: str, hashed: PasswordHash) -> bool:
        """Verifica que la plain text coincida con el hash. Retorna bool (sin lanzar)."""
        ...