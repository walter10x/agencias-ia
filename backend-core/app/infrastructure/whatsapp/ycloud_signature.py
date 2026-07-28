"""Verificación de firma HMAC de webhooks YCloud.

Header: ``YCloud-Signature: t={unix_seconds},s={hex_hmac}``
Payload firmado: ``{timestamp}.{raw_body}``
Algoritmo: HMAC-SHA256 con el secret del endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import time


def parse_ycloud_signature_header(header: str) -> tuple[str, str] | None:
    """Extrae (timestamp, signature) del header. None si el formato es inválido."""
    if not header or not header.strip():
        return None

    parts: dict[str, str] = {}
    for chunk in header.split(","):
        chunk = chunk.strip()
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        parts[key.strip()] = value.strip()

    timestamp = parts.get("t", "")
    signature = parts.get("s", "")
    if not timestamp or not signature:
        return None
    return timestamp, signature


def verify_ycloud_signature(
    raw_body: bytes | str,
    signature_header: str,
    secret: str,
    *,
    max_age_seconds: int = 300,
    now: int | None = None,
) -> bool:
    """Valida la firma HMAC-SHA256 de YCloud.

    Si ``secret`` está vacío, retorna False (el caller decide si exigir firma).
    """
    if not secret:
        return False

    parsed = parse_ycloud_signature_header(signature_header)
    if parsed is None:
        return False

    timestamp, signature = parsed
    try:
        ts = int(timestamp)
    except ValueError:
        return False

    current = now if now is not None else int(time.time())
    if abs(current - ts) > max_age_seconds:
        return False

    if isinstance(raw_body, bytes):
        body_str = raw_body.decode("utf-8")
    else:
        body_str = raw_body

    signed_payload = f"{timestamp}.{body_str}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
