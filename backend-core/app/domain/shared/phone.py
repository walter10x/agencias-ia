"""Normalización de teléfonos para CRM / matching multi-módulo.

Vive en domain/shared (sin I/O). Usado por application al agregar
lead + conversation + appointment por la misma persona.
"""

from __future__ import annotations


def normalize_phone(raw: str) -> str:
    """Devuelve E.164 simple: dígitos con prefijo '+' si hay contenido.

    No valida país; solo unifica formato para comparar.
    """
    cleaned = (raw or "").strip().replace(" ", "").replace("-", "")
    if not cleaned:
        return ""
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if not digits:
        return ""
    return f"+{digits}"


def phones_match(a: str, b: str) -> bool:
    """True si ambos normalizan al mismo E.164."""
    na = normalize_phone(a)
    nb = normalize_phone(b)
    return bool(na) and na == nb
