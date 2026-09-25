import hashlib
import hmac
import json

from tests.pdf_fixture import make_pdf_bytes

from app.billing import limits
from app.core.config import get_settings


async def _signup_and_get_org(client, email: str) -> str:
    await client.post("/auth/signup", json={"email": email, "password": "correcthorse123"})
    return (await client.get("/organizations")).json()[0]["id"]


async def _upload(client, org_id: str, filename: str) -> object:
    return await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": (filename, make_pdf_bytes(["Some content."]), "application/pdf")},
    )


async def _activate_subscription(client, monkeypatch, org_id: str) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "shh-its-a-secret")
    body = json.dumps(
        {
            "meta": {"event_name": "subscription_created", "custom_data": {"organization_id": org_id}},
            "data": {
                "id": "1",
                "attributes": {
                    "status": "active",
                    "customer_id": 1,
                    "variant_id": 1,
                    "variant_name": "Pro",
                    "renews_at": "2026-11-01T00:00:00.000000Z",
                    "ends_at": None,
                },
            },
        }
    ).encode()
    signature = hmac.new(b"shh-its-a-secret", body, hashlib.sha256).hexdigest()
    response = await client.post("/billing/lemonsqueezy/webhook", content=body, headers={"X-Signature": signature})
    assert response.status_code == 204


async def test_free_plan_blocks_uploads_past_the_document_limit(client):
    org_id = await _signup_and_get_org(client, "limits1@example.com")

    for i in range(limits.FREE_DOCUMENT_LIMIT):
        response = await _upload(client, org_id, f"doc{i}.pdf")
        assert response.status_code == 201

    blocked = await _upload(client, org_id, "one_too_many.pdf")
    assert blocked.status_code == 402
    assert "free plan" in blocked.json()["detail"].lower()


async def test_active_subscription_lifts_the_document_limit(client, monkeypatch):
    org_id = await _signup_and_get_org(client, "limits2@example.com")
    await _activate_subscription(client, monkeypatch, org_id)

    for i in range(limits.FREE_DOCUMENT_LIMIT + 2):
        response = await _upload(client, org_id, f"doc{i}.pdf")
        assert response.status_code == 201


async def test_free_plan_blocks_chat_past_the_message_limit(client, monkeypatch):
    monkeypatch.setattr(limits, "FREE_MESSAGE_LIMIT", 1)
    org_id = await _signup_and_get_org(client, "limits3@example.com")

    first = await client.post(f"/organizations/{org_id}/chat", json={"message": "Hello"})
    assert first.status_code == 200

    second = await client.post(f"/organizations/{org_id}/chat", json={"message": "Hello again"})
    assert second.status_code == 402
    assert "free plan" in second.json()["detail"].lower()


async def test_usage_endpoint_reflects_real_counts(client):
    org_id = await _signup_and_get_org(client, "limits5@example.com")

    before = (await client.get(f"/organizations/{org_id}/billing/usage")).json()
    assert before["is_paid_plan"] is False
    assert before["document_count"] == 0
    assert before["document_limit"] == limits.FREE_DOCUMENT_LIMIT

    await _upload(client, org_id, "doc.pdf")

    after = (await client.get(f"/organizations/{org_id}/billing/usage")).json()
    assert after["document_count"] == 1


async def test_active_subscription_lifts_the_message_limit(client, monkeypatch):
    monkeypatch.setattr(limits, "FREE_MESSAGE_LIMIT", 1)
    org_id = await _signup_and_get_org(client, "limits4@example.com")
    await _activate_subscription(client, monkeypatch, org_id)

    first = await client.post(f"/organizations/{org_id}/chat", json={"message": "Hello"})
    assert first.status_code == 200
    second = await client.post(f"/organizations/{org_id}/chat", json={"message": "Hello again"})
    assert second.status_code == 200
