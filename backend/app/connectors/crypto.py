from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class ConnectorEncryptionNotConfiguredError(Exception):
    """No CONNECTOR_ENCRYPTION_KEY is set. Mirrors LLMNotConfiguredError's
    pattern: a missing secret is a clear, caught error, not a crash."""


@lru_cache
def _get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.connector_encryption_key:
        raise ConnectorEncryptionNotConfiguredError(
            "No CONNECTOR_ENCRYPTION_KEY configured. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "and set it in backend/.env."
        )
    return Fernet(settings.connector_encryption_key.encode())


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ConnectorEncryptionNotConfiguredError(
            "Stored token could not be decrypted -- CONNECTOR_ENCRYPTION_KEY may have changed"
        ) from exc
