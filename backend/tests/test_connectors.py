import uuid

from app.connectors import google_oauth, oauth_state, slack_oauth


async def _signup_and_get_org(client, email: str) -> tuple[str, str]:
    user = (await client.post("/auth/signup", json={"email": email, "password": "correcthorse123"})).json()
    org_id = (await client.get("/organizations")).json()[0]["id"]
    return org_id, user["id"]


async def test_authorize_requires_owner_or_admin(client, second_client):
    org_id, _owner_id = await _signup_and_get_org(client, "conn_owner1@example.com")
    await second_client.post("/auth/signup", json={"email": "conn_member1@example.com", "password": "correcthorse123"})
    await client.post(f"/organizations/{org_id}/members", json={"email": "conn_member1@example.com", "role": "member"})

    response = await second_client.get(f"/organizations/{org_id}/connectors/google/authorize")

    assert response.status_code == 403


async def test_authorize_returns_a_google_url_for_owner(client):
    org_id, _owner_id = await _signup_and_get_org(client, "conn_owner2@example.com")

    response = await client.get(f"/organizations/{org_id}/connectors/google/authorize")

    assert response.status_code == 200
    url = response.json()["authorize_url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=" in url
    assert "gmail.readonly" in url


async def test_callback_with_invalid_state_is_rejected(client):
    await _signup_and_get_org(client, "conn_owner3@example.com")

    response = await client.get("/connectors/google/callback", params={"code": "fake", "state": "not-a-real-nonce"})

    assert response.status_code == 400


async def test_callback_completes_and_creates_a_connector(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "conn_owner4@example.com")

    async def fake_exchange(code: str) -> dict:
        return {"access_token": "fake-access", "refresh_token": "fake-refresh", "expires_in": 3600, "scope": "gmail.readonly"}

    async def fake_fetch_email(access_token: str) -> str:
        return "connected-account@gmail.com"

    monkeypatch.setattr(google_oauth, "exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(google_oauth, "fetch_user_email", fake_fetch_email)

    import uuid

    nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
    response = await client.get(
        "/connectors/google/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False
    )

    assert response.status_code in (302, 307)

    listing = await client.get(f"/organizations/{org_id}/connectors")
    assert listing.status_code == 200
    accounts = listing.json()
    assert len(accounts) == 1
    assert accounts[0]["account_label"] == "connected-account@gmail.com"
    assert accounts[0]["provider"] == "google"


async def test_callback_state_cannot_be_reused(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "conn_owner5@example.com")

    async def fake_exchange(code: str) -> dict:
        return {"access_token": "fake-access", "refresh_token": "fake-refresh", "expires_in": 3600, "scope": "gmail.readonly"}

    async def fake_fetch_email(access_token: str) -> str:
        return "reused@gmail.com"

    monkeypatch.setattr(google_oauth, "exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(google_oauth, "fetch_user_email", fake_fetch_email)

    import uuid

    nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
    first = await client.get(
        "/connectors/google/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False
    )
    assert first.status_code in (302, 307)

    second = await client.get(
        "/connectors/google/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False
    )
    assert second.status_code == 400


async def test_list_recent_emails_and_delete_connector(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "conn_owner6@example.com")

    async def fake_exchange(code: str) -> dict:
        return {"access_token": "fake-access", "refresh_token": "fake-refresh", "expires_in": 3600, "scope": "gmail.readonly"}

    async def fake_fetch_email(access_token: str) -> str:
        return "emails@gmail.com"

    async def fake_list_messages(access_token: str, max_results: int = 10) -> list[dict]:
        return [{"id": "1", "subject": "Hello", "from": "sender@example.com", "date": "today", "snippet": "hi there"}]

    monkeypatch.setattr(google_oauth, "exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(google_oauth, "fetch_user_email", fake_fetch_email)
    monkeypatch.setattr(google_oauth, "list_recent_messages", fake_list_messages)

    import uuid

    nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
    await client.get("/connectors/google/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False)

    connector_id = (await client.get(f"/organizations/{org_id}/connectors")).json()[0]["id"]

    emails = await client.get(f"/organizations/{org_id}/connectors/{connector_id}/emails")
    assert emails.status_code == 200
    assert emails.json()[0]["sender"] == "sender@example.com"

    deleted = await client.delete(f"/organizations/{org_id}/connectors/{connector_id}")
    assert deleted.status_code == 204

    missing = await client.get(f"/organizations/{org_id}/connectors/{connector_id}/emails")
    assert missing.status_code == 404


async def test_slack_authorize_returns_a_slack_url_for_owner(client):
    org_id, _owner_id = await _signup_and_get_org(client, "conn_slack_owner1@example.com")

    response = await client.get(f"/organizations/{org_id}/connectors/slack/authorize")

    assert response.status_code == 200
    url = response.json()["authorize_url"]
    assert url.startswith("https://slack.com/oauth/v2/authorize?")
    assert "client_id=" in url


async def test_slack_callback_completes_and_creates_a_connector(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "conn_slack_owner2@example.com")

    async def fake_exchange(code: str) -> dict:
        return {
            "ok": True,
            "access_token": "xoxb-fake",
            "scope": "channels:read",
            "team": {"id": "T123", "name": "Ogem Systems"},
        }

    monkeypatch.setattr(slack_oauth, "exchange_code_for_token", fake_exchange)

    nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
    response = await client.get(
        "/connectors/slack/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False
    )

    assert response.status_code in (302, 307)

    accounts = (await client.get(f"/organizations/{org_id}/connectors")).json()
    assert len(accounts) == 1
    assert accounts[0]["provider"] == "slack"
    assert accounts[0]["account_label"] == "Ogem Systems"


async def test_slack_channels_are_listed_through_the_stored_connector(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "conn_slack_owner3@example.com")

    async def fake_exchange(code: str) -> dict:
        return {"ok": True, "access_token": "xoxb-fake", "scope": "channels:read", "team": {"name": "Ogem Systems"}}

    async def fake_list_channels(access_token: str, limit: int = 20) -> list[dict]:
        return [{"id": "C1", "name": "general", "is_member": True, "num_members": 5}]

    monkeypatch.setattr(slack_oauth, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(slack_oauth, "list_channels", fake_list_channels)

    nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
    await client.get("/connectors/slack/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False)

    connector_id = (await client.get(f"/organizations/{org_id}/connectors")).json()[0]["id"]

    channels = await client.get(f"/organizations/{org_id}/connectors/{connector_id}/channels")
    assert channels.status_code == 200
    assert channels.json()[0]["name"] == "general"


async def test_gmail_emails_route_rejects_a_slack_connector_id(client, monkeypatch):
    org_id, user_id = await _signup_and_get_org(client, "conn_slack_owner4@example.com")

    async def fake_exchange(code: str) -> dict:
        return {"ok": True, "access_token": "xoxb-fake", "scope": "channels:read", "team": {"name": "Ogem Systems"}}

    monkeypatch.setattr(slack_oauth, "exchange_code_for_token", fake_exchange)

    nonce = oauth_state.create_state(uuid.UUID(org_id), uuid.UUID(user_id))
    await client.get("/connectors/slack/callback", params={"code": "fake-code", "state": nonce}, follow_redirects=False)

    connector_id = (await client.get(f"/organizations/{org_id}/connectors")).json()[0]["id"]

    response = await client.get(f"/organizations/{org_id}/connectors/{connector_id}/emails")
    assert response.status_code == 404
