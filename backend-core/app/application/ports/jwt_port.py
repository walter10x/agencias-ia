"""Puerto Jwt — abstracción para firmar/verificar tokens JWT.

La capa de aplicación define este puerto. La infraestructura provee
el adaptador concreto JoseJwtHandler (HS256 vía python-jose).
El dominio NO conoce jose.
"""

from __future__ import annotations

from typing import Any, Protocol


class JwtPort(Protocol):
    """Interfaz para firmar y decodificar tokens JWT."""

    def sign(self, sub: str, role: str, client_id: str | None) -> str:
        """Firma un token JWT con los claims sub, role, client_id y exp."""
        ...

    def decode(self, token: str) -> dict[str, Any]:
        """Decodifica y verifica un token JWT. Lanza UnauthorizedError si inválido/expirado."""
        ...