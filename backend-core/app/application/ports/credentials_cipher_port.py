"""Puerto de cifrado simétrico de credenciales (DRIVEN PORT).

La capa de aplicación cifra/descifra secretos (p. ej. el access token
de Meta Cloud API) sin conocer el algoritmo concreto. La implementación
vive en infrastructure/security/credentials_cipher.py (Fernet).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CredentialsCipherPort(ABC):
    """Cifrado/descifrado simétrico de credenciales sensibles."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Cifra un secreto y devuelve el ciphertext serializado (str)."""
        ...

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Descifra un ciphertext previamente producido por encrypt()."""
        ...
