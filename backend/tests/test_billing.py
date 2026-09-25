import hashlib
import hmac
import json

from app.billing import lemonsqueezy
from app.core.config import get_settings


async def _signup_and_get_org(client, email: str) -> str:
    await client.post("/auth/signup", json={"email": email, "password": "correcthorse123"})
    return (await client.get("/organizations")).json()[0]["id"]


def test_verify_webhook_signature_accepts_correctly_signed_body(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "shh-its-a-secret")
    body = b'{"hello": "world"}'
    signature = hmac.new(b"shh-its-a-secret", body, hashlib.sha256).hexdigest()

    assert lemonsqueezy.verify_webhook_signature(body, signature) is True


def test_verify_webhook_signature_rejects_tampered_body(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "shh-its-a-secret")
    body = b'{"hello": "world"}'
    signature = hmac.new(b"shh-its-a-secret", body, hashlib.sha256).hexdigest()

    assert lemonsqueezy.verify_webhook_signature(b'{"hello": "tampered"}', signature) is False


def test_verify_webhook_signature_rejects_missing_signature(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "shh-its-a-secret")

    assert lemonsqueezy.verify_webhook_signature(b"{}", None) is False


async def test_checkout_requires_owner_or_admin(client, second_client):
    org_id = await _signup_and_get_org(client, "billing1@example.com")
    await second_client.post("/auth/signup", json={"email": "billing1member@example.com", "password": "correcthorse123"})
    await client.post(f"/organizations/{org_id}/members", json={"email": "billing1member@example.com", "role": "member"})

    response = await second_client.post(f"/organizations/{org_id}/billing/checkout")

    assert response.status_code == 403


async def test_subscription_is_null_before_any_webhook(client):
    org_id = await _signup_and_get_org(client, "billing2@example.com")

    response = await client.get(f"/organizations/{org_id}/billing/subscription")

    assert response.status_code == 200
    assert response.json() is None


async def test_webhook_with_bad_signature_is_rejected(client):
    org_id = await _signup_and_get_org(client, "billing3@example.com")
    body = json.dumps(
        {
            "meta": {"event_name": "subscription_created", "custom_data": {"organization_id": org_id}},
            "data": {"id": "999", "attributes": {"status": "active", "customer_id": 1, "variant_id": 1, "variant_name": "Pro"}},
        }
    ).encode()

    response = await client.post(
        "/billing/lemonsqueezy/webhook", content=body, headers={"X-Signature": "not-a-real-signature"}
    )

    assert response.status_code == 401


async def test_webhook_creates_and_then_updates_a_subscription(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "shh-its-a-secret")
    org_id = await _signup_and_get_org(client, "billing4@example.com")

    created_body = json.dumps(
        {
            "meta": {"event_name": "subscription_created", "custom_data": {"organization_id": org_id}},
            "data": {
                "id": "555",
                "attributes": {
                    "status": "active",
                    "customer_id": 42,
                    "variant_id": 7,
                    "variant_name": "Pro Monthly",
                    "renews_at": "2026-11-01T00:00:00.000000Z",
                    "ends_at": None,
                },
            },
        }
    ).encode()
    signature = hmac.new(b"shh-its-a-secret", created_body, hashlib.sha256).hexdigest()

    created = await client.post(
        "/billing/lemonsqueezy/webhook", content=created_body, headers={"X-Signature": signature}
    )
    assert created.status_code == 204

    subscription = (await client.get(f"/organizations/{org_id}/billing/subscription")).json()
    assert subscription["status"] == "active"
    assert subscription["variant_name"] == "Pro Monthly"

    # A later "cancelled" event for the same org updates the same row.
    cancelled_body = json.dumps(
        {
            "meta": {"event_name": "subscription_cancelled", "custom_data": {"organization_id": org_id}},
            "data": {
                "id": "555",
                "attributes": {
                    "status": "cancelled",
                    "customer_id": 42,
                    "variant_id": 7,
                    "variant_name": "Pro Monthly",
                    "renews_at": None,
                    "ends_at": "2026-12-01T00:00:00.000000Z",
                },
            },
        }
    ).encode()
    signature2 = hmac.new(b"shh-its-a-secret", cancelled_body, hashlib.sha256).hexdigest()

    cancelled = await client.post(
        "/billing/lemonsqueezy/webhook", content=cancelled_body, headers={"X-Signature": signature2}
    )
    assert cancelled.status_code == 204

    subscription = (await client.get(f"/organizations/{org_id}/billing/subscription")).json()
    assert subscription["status"] == "cancelled"


async def test_webhook_ignores_non_subscription_events(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "shh-its-a-secret")
    org_id = await _signup_and_get_org(client, "billing5@example.com")

    body = json.dumps(
        {"meta": {"event_name": "order_created", "custom_data": {"organization_id": org_id}}, "data": {"id": "1", "attributes": {}}}
    ).encode()
    signature = hmac.new(b"shh-its-a-secret", body, hashlib.sha256).hexdigest()

    response = await client.post("/billing/lemonsqueezy/webhook", content=body, headers={"X-Signature": signature})

    assert response.status_code == 204
    assert (await client.get(f"/organizations/{org_id}/billing/subscription")).json() is None
