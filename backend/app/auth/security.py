import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def generate_session_token() -> str:
    """Raw token that goes in the cookie. Never stored as-is in the database."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """One-way hash stored in the database, so a DB leak alone can't be used as a session."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
