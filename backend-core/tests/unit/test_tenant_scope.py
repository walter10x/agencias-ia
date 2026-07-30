"""Tests for resolve_list_client_id."""

from __future__ import annotations

import pytest

from app.application.shared.tenant_scope import (
    TenantScopeError,
    resolve_list_client_id,
)


def test_superadmin_uses_requested_client_id() -> None:
    assert resolve_list_client_id("superadmin", "own", "orinoco-id") == "orinoco-id"


def test_superadmin_requires_client_id() -> None:
    with pytest.raises(TenantScopeError):
        resolve_list_client_id("superadmin", "own", None)


def test_client_admin_ignores_requested_id() -> None:
    assert resolve_list_client_id("client_admin", "own-id", "other-id") == "own-id"
