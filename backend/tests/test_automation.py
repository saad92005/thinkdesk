import pytest
import uuid

from app.connectors import google_oauth, oauth_state, slack_oauth
from tests.pdf_fixture import make_pdf_bytes


async def _upload(client, org_id: str, filename: str, lines: list[str]) -> str:
    upload = await client.post(
        f"/organizations/{org_id}/documents",
        files={"file": (filename, make_pdf_bytes(lines), "application/pdf")},
    )
    return upload.json()["id"]


async def _connect_slack(client, org_id: str, user_id: str) -> str:
    async def fake_exchange(code: str) -> dict:
        return {"ok": True, "access_token": "xoxb-fake", "scope": "channels:read,chat:write", "team": {"name": "Automation Test"}}

    import unittest.mock

    with unittest.mock.patch.object(slack_oauth, "exchange_code_for_token", fake_exchange):
        nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
        await client.get("/connectors/slack/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False)

    connectors = (await client.get(f"/organizations/{org_id}/connectors")).json()
    return next(c["id"] for c in connectors if c["provider"] == "slack")


async def _signup_and_get_org(client, email: str) -> tuple[str, str]:
    user = (await client.post("/auth/signup", json={"email": email, "password": "correcthorse123"})).json()
    org_id = (await client.get("/organizations")).json()[0]["id"]
    return org_id, user["id"]


@pytest.mark.live_llm
async def test_document_automation_rule_runs_and_queues_a_draft(client):
    org_id, user_id = await _signup_and_get_org(client, "automation1@example.com")
    slack_id = await _connect_slack(client, org_id, user_id)
    doc_id = await _upload(client, org_id, "onboarding.pdf", ["New hires get a laptop within their first week."])

    create = await client.post(
        f"/organizations/{org_id}/automations",
        json={
            "name": "Weekly onboarding digest",
            "source": "document",
            "document_id": doc_id,
            "slack_connector_id": slack_id,
            "channel_id": "C111",
        },
    )
    assert create.status_code == 201
    rule_id = create.json()["id"]

    run = await client.post(f"/organizations/{org_id}/automations/{rule_id}/run")
    assert run.status_code == 200
    body = run.json()
    assert body["rule_name"] == "Weekly onboarding digest"
    assert body["status"] == "pending"
    assert isinstance(body["draft_text"], str) and body["draft_text"]

    queue = await client.get(f"/organizations/{org_id}/automations/queue")
    assert queue.status_code == 200
    assert len(queue.json()) == 1


@pytest.mark.live_llm
async def test_approving_a_queued_draft_posts_exactly_that_text(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "automation2@example.com")
    slack_id = await _connect_slack(client, org_id, user_id)
    doc_id = await _upload(client, org_id, "policy.pdf", ["Refunds are honored within 30 days."])

    create = await client.post(
        f"/organizations/{org_id}/automations",
        json={"name": "Policy digest", "source": "document", "document_id": doc_id, "slack_connector_id": slack_id, "channel_id": "C222"},
    )
    rule_id = create.json()["id"]
    run = await client.post(f"/organizations/{org_id}/automations/{rule_id}/run")
    draft_id = run.json()["id"]

    captured = {}

    async def fake_post_message(access_token: str, channel: str, text: str) -> dict:
        captured["channel"] = channel
        captured["text"] = text
        return {"ok": True, "ts": "999.111"}

    monkeypatch.setattr(slack_oauth, "post_message", fake_post_message)

    approve = await client.post(
        f"/organizations/{org_id}/automations/queue/{draft_id}/approve", json={"message": "Edited by a human before sending"}
    )
    assert approve.status_code == 200
    assert approve.json()["slack_ts"] == "999.111"
    assert captured["text"] == "Edited by a human before sending"

    queue = await client.get(f"/organizations/{org_id}/automations/queue")
    assert queue.json() == []


@pytest.mark.live_llm
async def test_approving_requires_owner_or_admin(client, second_client):
    org_id, owner_id = await _signup_and_get_org(client, "automation3@example.com")
    slack_id = await _connect_slack(client, org_id, owner_id)
    doc_id = await _upload(client, org_id, "policy.pdf", ["Some content."])

    create = await client.post(
        f"/organizations/{org_id}/automations",
        json={"name": "Rule", "source": "document", "document_id": doc_id, "slack_connector_id": slack_id, "channel_id": "C333"},
    )
    rule_id = create.json()["id"]
    run = await client.post(f"/organizations/{org_id}/automations/{rule_id}/run")
    draft_id = run.json()["id"]

    await second_client.post("/auth/signup", json={"email": "automation3member@example.com", "password": "correcthorse123"})
    await client.post(f"/organizations/{org_id}/members", json={"email": "automation3member@example.com", "role": "member"})

    response = await second_client.post(
        f"/organizations/{org_id}/automations/queue/{draft_id}/approve", json={"message": "hi"}
    )
    assert response.status_code == 403


@pytest.mark.live_llm
async def test_dismissing_a_queued_draft_removes_it_from_the_queue(client):
    org_id, user_id = await _signup_and_get_org(client, "automation4@example.com")
    slack_id = await _connect_slack(client, org_id, user_id)
    doc_id = await _upload(client, org_id, "notes.pdf", ["Team meeting moved to Thursday."])

    create = await client.post(
        f"/organizations/{org_id}/automations",
        json={"name": "Notes digest", "source": "document", "document_id": doc_id, "slack_connector_id": slack_id, "channel_id": "C444"},
    )
    rule_id = create.json()["id"]
    run = await client.post(f"/organizations/{org_id}/automations/{rule_id}/run")
    draft_id = run.json()["id"]

    dismiss = await client.post(f"/organizations/{org_id}/automations/queue/{draft_id}/dismiss")
    assert dismiss.status_code == 204

    queue = await client.get(f"/organizations/{org_id}/automations/queue")
    assert queue.json() == []


async def test_gmail_automation_rule_requires_gmail_connector_id(client):
    org_id, user_id = await _signup_and_get_org(client, "automation5@example.com")
    slack_id = await _connect_slack(client, org_id, user_id)

    response = await client.post(
        f"/organizations/{org_id}/automations",
        json={"name": "Bad rule", "source": "gmail", "slack_connector_id": slack_id, "channel_id": "C555"},
    )
    assert response.status_code == 400
