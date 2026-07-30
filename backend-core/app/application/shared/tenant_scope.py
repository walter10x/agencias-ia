"""Resolución de tenant para listados (superadmin vs client_admin)."""

from __future__ import annotations


class TenantScopeError(ValueError):
    """client_id inválido o faltante para el rol actual."""


def resolve_list_client_id(
    role: str,
    own_client_id: str,
    requested_client_id: str | None,
) -> str:
    """client_admin → siempre own. superadmin → requested obligatorio."""
    if role == "superadmin":
        cid = (requested_client_id or "").strip()
        if not cid:
            raise TenantScopeError("client_id is required for superadmin")
        return cid
    return own_client_id
