#!/usr/bin/env python3
"""Idempotent seed script: creates or updates the superadmin in Supabase.

Usage:
    SUPERADMIN_EMAIL=admin@example.com SUPERADMIN_PASSWORD=<contraseña-fuerte> \
        python scripts/seed_superadmin.py

Environment variables (AMBAS obligatorias, sin defaults):
    SUPERADMIN_EMAIL    — email del superadmin a crear/actualizar.
    SUPERADMIN_PASSWORD — password en texto plano (se hashea con bcrypt antes
                          de persistir). Genera una fuerte, ej.:
                          python3 -c "import secrets; print(secrets.token_urlsafe(18))"

Nota de seguridad (Fase 0.2/0.3 saneamiento): este script NO tiene defaults
hardcodeados para email/password. Antes tenía "walter@admin.com" /
"SuperAdmin123!" como fallback, lo que quedó además documentado en texto
plano en GUIA-INTEGRACION.md. Si ese admin llegó a crearse en algún entorno
real con esas credenciales, hay que rotarlas (ver SECURITY-TODO.md).
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

    email = _get_env_or_fail("SUPERADMIN_EMAIL")
    password = _get_env_or_fail("SUPERADMIN_PASSWORD")

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
