from app.connectors import notion_client


async def _signup_and_get_org(client, email: str) -> str:
    await client.post("/auth/signup", json={"email": email, "password": "correcthorse123"})
    return (await client.get("/organizations")).json()[0]["id"]


async def test_connect_notion_requires_owner_or_admin(client, second_client, monkeypatch):
    org_id = await _signup_and_get_org(client, "notion1@example.com")
    await second_client.post("/auth/signup", json={"email": "notion1member@example.com", "password": "correcthorse123"})
    await client.post(f"/organizations/{org_id}/members", json={"email": "notion1member@example.com", "role": "member"})

    response = await second_client.post(f"/organizations/{org_id}/connectors/notion", json={"token": "fake"})

    assert response.status_code == 403


async def test_connect_notion_rejects_an_invalid_token(client, monkeypatch):
    org_id = await _signup_and_get_org(client, "notion2@example.com")

    async def fake_verify(token: str) -> dict:
        raise notion_client.NotionTokenInvalidError("bad token")

    monkeypatch.setattr(notion_client, "verify_token", fake_verify)

    response = await client.post(f"/organizations/{org_id}/connectors/notion", json={"token": "not-real"})

    assert response.status_code == 400


async def test_connect_notion_and_list_pages(client, monkeypatch):
    org_id = await _signup_and_get_org(client, "notion3@example.com")

    async def fake_verify(token: str) -> dict:
        return {"label": "Test Workspace"}

    async def fake_search(token: str, page_size: int = 20) -> list[dict]:
        return [{"id": "abc", "object": "page", "title": "Roadmap", "url": "https://notion.so/abc"}]

    monkeypatch.setattr(notion_client, "verify_token", fake_verify)
    monkeypatch.setattr(notion_client, "search_pages", fake_search)

    connect = await client.post(f"/organizations/{org_id}/connectors/notion", json={"token": "fake-token"})
    assert connect.status_code == 201
    body = connect.json()
    assert body["provider"] == "notion"
    assert body["account_label"] == "Test Workspace"

    pages = await client.get(f"/organizations/{org_id}/connectors/{body['id']}/pages")
    assert pages.status_code == 200
    assert pages.json()[0]["title"] == "Roadmap"


async def test_verify_token_against_the_real_notion_api():
    """Uses the real token configured in backend/.env to confirm the
    integration actually works against Notion's live API, not just our
    own mocks."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.notion_api_key:
        return  # No token configured in this environment -- skip rather than fail.

    info = await notion_client.verify_token(settings.notion_api_key)
    assert isinstance(info["label"], str) and info["label"]
