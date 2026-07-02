"""Enums para el agregado Client."""

from __future__ import annotations

from enum import Enum


class ClientRole(str, Enum):
    SUPERADMIN = "superadmin"
    CLIENT_ADMIN = "client_admin"
    CLIENT_USER = "client_user"


class ClientStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    INACTIVE = "inactive"