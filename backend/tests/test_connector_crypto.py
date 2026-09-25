import pytest

from app.connectors import crypto
from app.core.config import get_settings


def test_encrypt_decrypt_roundtrip():
    original = "a-fake-refresh-token"
    encrypted = crypto.encrypt(original)
    assert encrypted != original
    assert crypto.decrypt(encrypted) == original


def test_missing_key_raises_clear_error(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "connector_encryption_key", None)
    crypto._get_fernet.cache_clear()
    try:
        with pytest.raises(crypto.ConnectorEncryptionNotConfiguredError):
            crypto.encrypt("anything")
    finally:
        crypto._get_fernet.cache_clear()
