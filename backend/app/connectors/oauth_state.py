import secrets
import time
import uuid

# In-memory, single-process store for the OAuth "state" round trip: ties a
# nonce to the org+user that started the flow, single-use (popped on
# consume) and short-lived. This is enough to stop a CSRF/login-CSRF
# attempt against a single-worker dev deployment; a multi-worker production
# deployment would need this in Redis (or the database) instead, since
# workers don't share process memory.
_PENDING: dict[str, tuple[uuid.UUID, uuid.UUID, float]] = {}
STATE_TTL_SECONDS = 600


def _cleanup() -> None:
    now = time.time()
    for key in [k for k, (_org, _user, expiry) in _PENDING.items() if expiry < now]:
        _PENDING.pop(key, None)


def create_state(organization_id: uuid.UUID, user_id: uuid.UUID) -> str:
    _cleanup()
    nonce = secrets.token_urlsafe(24)
    _PENDING[nonce] = (organization_id, user_id, time.time() + STATE_TTL_SECONDS)
    return nonce


def consume_state(nonce: str) -> tuple[uuid.UUID, uuid.UUID] | None:
    """Single-use: returns (organization_id, user_id) and removes the
    entry, or None if the state is unknown, already used, or expired."""
    _cleanup()
    entry = _PENDING.pop(nonce, None)
    if entry is None:
        return None
    organization_id, user_id, expiry = entry
    if time.time() > expiry:
        return None
    return organization_id, user_id
