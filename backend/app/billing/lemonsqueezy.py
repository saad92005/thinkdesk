import hashlib
import hmac
import uuid

import httpx

from app.core.config import get_settings

API_BASE = "https://api.lemonsqueezy.com/v1"


class LemonSqueezyNotConfiguredError(Exception):
    """Missing API key, store ID, or variant ID."""


class LemonSqueezyError(Exception):
    """A call to Lemon Squeezy's API failed."""


def _require_settings():
    settings = get_settings()
    if not settings.lemonsqueezy_api_key or not settings.lemonsqueezy_store_id or not settings.lemonsqueezy_variant_id:
        raise LemonSqueezyNotConfiguredError(
            "Lemon Squeezy isn't fully configured. Set LEMONSQUEEZY_API_KEY, LEMONSQUEEZY_STORE_ID, and "
            "LEMONSQUEEZY_VARIANT_ID in backend/.env (create a Product + Variant in the dashboard first)."
        )
    return settings


async def create_checkout_url(organization_id: uuid.UUID, email: str) -> str:
    """Creates a real hosted checkout session and returns its URL. The
    organization_id is embedded as custom_data so the webhook handler can
    tell which ThinkDesk workspace a later subscription event belongs to
    -- Lemon Squeezy echoes custom_data back on every event for this
    checkout's resulting subscription."""
    settings = _require_settings()
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": email,
                    "custom": {"organization_id": str(organization_id)},
                }
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": settings.lemonsqueezy_store_id}},
                "variant": {"data": {"type": "variants", "id": settings.lemonsqueezy_variant_id}},
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"{API_BASE}/checkouts", headers=headers, json=payload)
    if response.status_code >= 300:
        raise LemonSqueezyError(f"Creating checkout failed: {response.text}")
    return response.json()["data"]["attributes"]["url"]


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Lemon Squeezy signs every webhook with HMAC-SHA256 of the raw
    (unparsed) request body, hex-encoded, in the X-Signature header. This
    must run on the exact bytes received -- re-serializing parsed JSON
    before checking would silently break verification on any formatting
    difference."""
    settings = get_settings()
    if not settings.lemonsqueezy_webhook_secret or not signature_header:
        return False
    expected = hmac.new(settings.lemonsqueezy_webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
