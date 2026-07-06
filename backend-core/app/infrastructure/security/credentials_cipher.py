"""Adaptador de CredentialsCipherPort (DRIVEN ADAPTER).

Implementación real: Fernet (AES-128-CBC + HMAC) de la librería
`cryptography`, con la clave leída de `settings.credentials_encryption_key`
(env `CREDENTIALS_ENCRYPTION_KEY`).

Comportamiento explícito ante configuración incompleta (NO debe crashear
el arranque de la app):

1. Si `cryptography` SÍ está instalada y hay clave configurada:
   se usa Fernet real (`_FernetBackend`). Este es el único modo
   considerado seguro para producción.
2. Si `cryptography` NO está instalada, o no hay clave configurada:
   se degrada a un fallback base64 (`_InsecureBase64Backend`) que NO
   ofrece ninguna confidencialidad real (base64 es una codificación,
   no cifrado) — cualquiera con acceso a la BD puede decodificarlo
   trivialmente. Se emite un `logger.warning` en cada instanciación
   para que sea imposible pasarlo por alto en logs/monitoreo.
   Este modo existe SOLO para que el resto del sistema (migraciones,
   tests, entornos sandbox sin acceso a PyPI) siga funcionando sin
   crashear; NUNCA debe usarse en producción con tokens reales.

Cómo pasar a modo seguro real:
    1. Añadir `cryptography` a requirements.txt e instalarla.
    2. Generar una clave: `Fernet.generate_key()` (32 bytes url-safe b64).
    3. Configurar `CREDENTIALS_ENCRYPTION_KEY` en el entorno/Dokploy.
"""

from __future__ import annotations

import base64
import logging

from app.application.ports.credentials_cipher_port import CredentialsCipherPort

logger = logging.getLogger(__name__)

# Prefijo que distingue el ciphertext producido por cada backend, para que
# decrypt() no intente descifrar con el backend equivocado si la clave
# cambia de disponibilidad entre despliegues (defensivo, no crítico).
_FERNET_PREFIX = "fernet:"
_INSECURE_PREFIX = "insecure-b64:"

try:
    from cryptography.fernet import Fernet, InvalidToken

    _CRYPTOGRAPHY_AVAILABLE = True
except ImportError:  # pragma: no cover — depende del entorno de instalación
    _CRYPTOGRAPHY_AVAILABLE = False


class _InsecureBase64Backend:
    """Fallback SOLO-DEV: NO es cifrado, es codificación base64 reversible.

    Se activa únicamente cuando `cryptography` no está disponible o no
    hay `CREDENTIALS_ENCRYPTION_KEY` configurada. Cualquier texto
    codificado aquí puede ser decodificado por cualquiera sin necesitar
    ninguna clave. NUNCA usar en producción con secretos reales.
    """

    def __init__(self) -> None:
        logger.warning(
            "[SECURITY] CredentialsCipher está en modo FALLBACK INSEGURO "
            "(base64, NO es cifrado real). Esto ocurre porque falta la "
            "librería 'cryptography' y/o la variable de entorno "
            "CREDENTIALS_ENCRYPTION_KEY. Los tokens de WhatsApp guardados "
            "en este modo NO están protegidos. Configura ambas cosas antes "
            "de desplegar a producción."
        )

    def encrypt(self, plaintext: str) -> str:
        encoded = base64.urlsafe_b64encode(plaintext.encode("utf-8")).decode("ascii")
        return f"{_INSECURE_PREFIX}{encoded}"

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        payload = ciphertext
        if payload.startswith(_INSECURE_PREFIX):
            payload = payload[len(_INSECURE_PREFIX):]
        try:
            return base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8")
        except Exception as exc:  # noqa: BLE001 — ciphertext corrupto o de otro backend
            raise ValueError(f"No se pudo decodificar el valor (modo inseguro): {exc}") from exc


class _FernetBackend:
    """Backend real de cifrado simétrico usando Fernet (cryptography)."""

    def __init__(self, key: str) -> None:
        # Fernet exige una clave de 32 bytes url-safe base64-encoded.
        self._fernet = Fernet(key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        token = self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
        return f"{_FERNET_PREFIX}{token}"

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        payload = ciphertext
        if payload.startswith(_FERNET_PREFIX):
            payload = payload[len(_FERNET_PREFIX):]
        try:
            return self._fernet.decrypt(payload.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Token de cifrado inválido o clave incorrecta") from exc


class FernetCredentialsCipher(CredentialsCipherPort):
    """Adaptador de CredentialsCipherPort.

    Selecciona automáticamente el backend real (Fernet) o el fallback
    inseguro de desarrollo, según disponibilidad de `cryptography` y de
    la clave de entorno. Ver docstring del módulo para el detalle del
    comportamiento de degradación.
    """

    def __init__(self, encryption_key: str = "") -> None:
        self._key = (encryption_key or "").strip()

        if _CRYPTOGRAPHY_AVAILABLE and self._key:
            self._backend = _FernetBackend(self._key)
            self._insecure = False
        else:
            if not _CRYPTOGRAPHY_AVAILABLE:
                logger.warning(
                    "[SECURITY] La librería 'cryptography' no está instalada; "
                    "no se puede usar Fernet real. Añádela a requirements.txt "
                    "e instálala para cifrado real en producción."
                )
            if not self._key:
                logger.warning(
                    "[SECURITY] CREDENTIALS_ENCRYPTION_KEY no está configurada; "
                    "no se puede usar Fernet real hasta que se configure."
                )
            self._backend = _InsecureBase64Backend()
            self._insecure = True

    @property
    def is_insecure_fallback(self) -> bool:
        """True si se está usando el fallback base64 SOLO-DEV (no cifrado real)."""
        return self._insecure

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self._backend.encrypt(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        return self._backend.decrypt(ciphertext)
