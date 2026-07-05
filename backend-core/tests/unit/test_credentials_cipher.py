"""Unit tests de FernetCredentialsCipher — real (si cryptography está
disponible) y fallback base64 SOLO-DEV.
"""

from __future__ import annotations

import importlib

import pytest

from app.infrastructure.security import credentials_cipher as cipher_module
from app.infrastructure.security.credentials_cipher import FernetCredentialsCipher

CRYPTOGRAPHY_AVAILABLE = cipher_module._CRYPTOGRAPHY_AVAILABLE


class TestInsecureFallback:
    """Fallback base64 — se activa sin clave configurada (con o sin cryptography)."""

    def test_no_key_configured_uses_insecure_fallback(self) -> None:
        cipher = FernetCredentialsCipher(encryption_key="")
        assert cipher.is_insecure_fallback is True

    def test_encrypt_decrypt_roundtrip_insecure(self) -> None:
        cipher = FernetCredentialsCipher(encryption_key="")
        secret = "EAABsbCS...meta-token-example"

        ciphertext = cipher.encrypt(secret)

        assert ciphertext != secret  # no se guarda en claro
        assert cipher.decrypt(ciphertext) == secret

    def test_encrypt_empty_string_returns_empty(self) -> None:
        cipher = FernetCredentialsCipher(encryption_key="")
        assert cipher.encrypt("") == ""

    def test_decrypt_empty_string_returns_empty(self) -> None:
        cipher = FernetCredentialsCipher(encryption_key="")
        assert cipher.decrypt("") == ""

    def test_insecure_fallback_warns_at_runtime(self, caplog) -> None:
        with caplog.at_level("WARNING"):
            FernetCredentialsCipher(encryption_key="")
        assert any("FALLBACK INSEGURO" in r.message for r in caplog.records)


@pytest.mark.skipif(not CRYPTOGRAPHY_AVAILABLE, reason="cryptography no instalada en este entorno")
class TestFernetRealBackend:
    """Backend real — solo se ejercita si 'cryptography' está instalada."""

    def _generate_key(self) -> str:
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode("ascii")

    def test_uses_real_fernet_when_key_and_lib_present(self) -> None:
        key = self._generate_key()
        cipher = FernetCredentialsCipher(encryption_key=key)
        assert cipher.is_insecure_fallback is False

    def test_encrypt_decrypt_roundtrip_real(self) -> None:
        key = self._generate_key()
        cipher = FernetCredentialsCipher(encryption_key=key)
        secret = "EAABsbCS...meta-token-example"

        ciphertext = cipher.encrypt(secret)

        assert ciphertext != secret
        assert cipher.decrypt(ciphertext) == secret

    def test_wrong_key_fails_to_decrypt(self) -> None:
        key_a = self._generate_key()
        key_b = self._generate_key()
        cipher_a = FernetCredentialsCipher(encryption_key=key_a)
        cipher_b = FernetCredentialsCipher(encryption_key=key_b)

        ciphertext = cipher_a.encrypt("secret-token")

        with pytest.raises(ValueError):
            cipher_b.decrypt(ciphertext)

    def test_missing_library_forces_fallback(self, monkeypatch) -> None:
        monkeypatch.setattr(cipher_module, "_CRYPTOGRAPHY_AVAILABLE", False)
        key = self._generate_key()
        cipher = FernetCredentialsCipher(encryption_key=key)
        assert cipher.is_insecure_fallback is True
