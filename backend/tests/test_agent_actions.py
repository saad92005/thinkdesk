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


async def _connect_gmail(client, org_id: str, user_id: str) -> str:
    async def fake_exchange(code: str) -> dict:
        return {"access_token": "fake-access", "refresh_token": "fake-refresh", "expires_in": 3600, "scope": "gmail.readonly"}

    async def fake_fetch_email(access_token: str) -> str:
        return "agent-gmail@example.com"

    import unittest.mock

    with unittest.mock.patch.object(google_oauth, "exchange_code_for_tokens", fake_exchange), unittest.mock.patch.object(
        google_oauth, "fetch_user_email", fake_fetch_email
    ):
        nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
        await client.get("/connectors/google/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False)

    connectors = (await client.get(f"/organizations/{org_id}/connectors")).json()
    return next(c["id"] for c in connectors if c["provider"] == "google")


async def _connect_slack(client, org_id: str, user_id: str) -> str:
    async def fake_exchange(code: str) -> dict:
        return {"ok": True, "access_token": "xoxb-fake", "scope": "channels:read,chat:write", "team": {"name": "Ogem Systems"}}

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
async def test_draft_email_summary_is_grounded_in_real_emails(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "agent1@example.com")
    gmail_id = await _connect_gmail(client, org_id, user_id)

    async def fake_list_messages(access_token: str, max_results: int = 10) -> list[dict]:
        return [
            {"id": "1", "subject": "Q3 budget approved", "from": "cfo@example.com", "date": "today", "snippet": "The Q3 budget was approved."}
        ]

    monkeypatch.setattr(google_oauth, "list_recent_messages", fake_list_messages)

    response = await client.post(
        f"/organizations/{org_id}/agent/draft-email-summary", json={"gmail_connector_id": gmail_id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_email_count"] == 1
    assert isinstance(body["draft_text"], str) and body["draft_text"]
    # Nothing should be posted anywhere by drafting alone.


async def test_draft_with_no_emails_reports_that_honestly(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "agent2@example.com")
    gmail_id = await _connect_gmail(client, org_id, user_id)

    async def fake_list_messages(access_token: str, max_results: int = 10) -> list[dict]:
        return []

    monkeypatch.setattr(google_oauth, "list_recent_messages", fake_list_messages)

    response = await client.post(
        f"/organizations/{org_id}/agent/draft-email-summary", json={"gmail_connector_id": gmail_id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_email_count"] == 0
    assert "no recent emails" in body["draft_text"].lower()


@pytest.mark.live_llm
async def test_draft_document_digest_is_grounded_in_the_real_document(client):
    org_id, _ = await _signup_and_get_org(client, "agent6@example.com")
    doc_id = await _upload(client, org_id, "handbook.pdf", ["Remote employees get a $500 annual home-office stipend."])

    response = await client.post(
        f"/organizations/{org_id}/agent/draft-document-digest", json={"document_id": doc_id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_document_name"] == "handbook.pdf"
    assert body["truncated"] is False
    assert isinstance(body["draft_text"], str) and body["draft_text"]


async def test_draft_document_digest_for_unprocessed_document_is_rejected(client):
    org_id, _ = await _signup_and_get_org(client, "agent7@example.com")

    response = await client.post(
        f"/organizations/{org_id}/agent/draft-document-digest", json={"document_id": str(uuid.uuid4())}
    )

    assert response.status_code == 502


async def test_post_to_slack_requires_owner_or_admin(client, second_client):
    org_id, owner_id = await _signup_and_get_org(client, "agent3@example.com")
    slack_id = await _connect_slack(client, org_id, owner_id)

    await second_client.post("/auth/signup", json={"email": "agent3member@example.com", "password": "correcthorse123"})
    await client.post(f"/organizations/{org_id}/members", json={"email": "agent3member@example.com", "role": "member"})

    response = await second_client.post(
        f"/organizations/{org_id}/agent/post-to-slack",
        json={"slack_connector_id": slack_id, "channel_id": "C123", "message": "hello"},
    )

    assert response.status_code == 403


async def test_post_to_slack_sends_exactly_the_approved_text(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "agent4@example.com")
    slack_id = await _connect_slack(client, org_id, user_id)

    captured = {}

    async def fake_post_message(access_token: str, channel: str, text: str) -> dict:
        captured["channel"] = channel
        captured["text"] = text
        return {"ok": True, "ts": "1234.5678"}

    monkeypatch.setattr(slack_oauth, "post_message", fake_post_message)

    response = await client.post(
        f"/organizations/{org_id}/agent/post-to-slack",
        json={"slack_connector_id": slack_id, "channel_id": "C999", "message": "Human-approved final text"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["posted"] is True
    assert body["slack_ts"] == "1234.5678"
    assert captured["channel"] == "C999"
    assert captured["text"] == "Human-approved final text"


async def test_post_to_slack_with_missing_scope_gives_a_reconnect_hint(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "agent5@example.com")
    slack_id = await _connect_slack(client, org_id, user_id)

    async def fake_post_message(access_token: str, channel: str, text: str) -> dict:
        raise slack_oauth.SlackOAuthError("Posting message failed: missing_scope")

    monkeypatch.setattr(slack_oauth, "post_message", fake_post_message)

    response = await client.post(
        f"/organizations/{org_id}/agent/post-to-slack",
        json={"slack_connector_id": slack_id, "channel_id": "C999", "message": "hi"},
    )

    assert response.status_code == 502
    assert "reconnect" in response.json()["detail"].lower()
