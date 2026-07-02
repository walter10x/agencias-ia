#!/usr/bin/env python3
"""Idempotent seed script: creates or updates the superadmin (Walter) in Supabase.

Usage:
    SUPERADMIN_EMAIL=walter@admin.com SUPERADMIN_PASSWORD=segura123 \
        python scripts/seed_superadmin.py

Environment variables:
    SUPERADMIN_EMAIL    (default: walter@admin.com)
    SUPERADMIN_PASSWORD (default: SuperAdmin123!)
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

from dotenv import load_dotenv
from supabase import create_client, Client

# Ensure backend-core is on sys.path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.infrastructure.security.password_hasher import BcryptPasswordHasher


def _get_env_or_fail(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"ERROR: {key} is not set")
        sys.exit(1)
    return val


def main() -> None:
    load_dotenv()

    supabase_url = _get_env_or_fail("SUPABASE_URL")
    supabase_key = _get_env_or_fail("SUPABASE_SERVICE_KEY")

    email = os.environ.get("SUPERADMIN_EMAIL", "walter@admin.com")
    password = os.environ.get("SUPERADMIN_PASSWORD", "SuperAdmin123!")

    client: Client = create_client(supabase_url, supabase_key)
    hasher = BcryptPasswordHasher()
    password_hash = str(hasher.hash_password(password))

    existing = (
        client.table("clients")
        .select("id")
        .eq("email", email)
        .execute()
    )

    if existing.data:
        print(f"Superadmin {email} already exists (id={existing.data[0]['id']}). Updating password.")
        client.table("clients").update({
            "password_hash": password_hash,
            "role": "superadmin",
            "status": "active",
            "is_active": True,
        }).eq("email", email).execute()
    else:
        admin_id = str(uuid4())
        print(f"Creating superadmin {email} (id={admin_id}).")
        client.table("clients").insert({
            "id": admin_id,
            "name": "Walter",
            "email": email,
            "password_hash": password_hash,
            "role": "superadmin",
            "status": "active",
            "is_active": True,
            "business_type": "otro",
            "whatsapp_number": "0000000000",
            "plan": "enterprise",
            "phone_number_id": "",
            "whatsapp_connected": False,
        }).execute()

    print("Done.")


if __name__ == "__main__":
    main()
