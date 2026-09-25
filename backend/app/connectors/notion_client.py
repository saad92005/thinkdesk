import httpx

NOTION_VERSION = "2022-06-28"
USERS_ME_URL = "https://api.notion.com/v1/users/me"
SEARCH_URL = "https://api.notion.com/v1/search"


class NotionTokenInvalidError(Exception):
    """The given token was rejected by Notion's API -- wrong, revoked, or
    never a real integration token."""


class NotionError(Exception):
    """A call to Notion's API failed."""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION}


async def verify_token(token: str) -> dict:
    """Confirms the token is real by asking Notion who it belongs to --
    this is also how we get a human-readable label for it (the
    integration/workspace name), since Notion's internal-integration
    tokens don't come with one built in the way an OAuth response does."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(USERS_ME_URL, headers=_headers(token))
    if response.status_code == 401:
        raise NotionTokenInvalidError("That token was rejected by Notion -- check it was copied correctly")
    if response.status_code != 200:
        raise NotionError(f"Verifying token failed: {response.text}")

    body = response.json()
    bot = body.get("bot", {})
    owner = bot.get("owner", {})
    workspace_name = bot.get("workspace_name")
    label = workspace_name or body.get("name") or owner.get("type") or "Notion workspace"
    return {"label": label}


async def search_pages(token: str, page_size: int = 20) -> list[dict]:
    """Lists pages and databases the integration has actually been given
    access to (shared with it inside Notion) -- an integration token alone
    grants nothing until the user shares specific pages with it, so an
    empty result here is a real, expected state, not a bug."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            SEARCH_URL, headers=_headers(token), json={"page_size": page_size}
        )
    if response.status_code != 200:
        raise NotionError(f"Searching pages failed: {response.text}")

    results = []
    for item in response.json().get("results", []):
        title = _extract_title(item)
        results.append(
            {
                "id": item["id"],
                "object": item.get("object", "page"),
                "title": title,
                "url": item.get("url", ""),
            }
        )
    return results


def _extract_title(item: dict) -> str:
    properties = item.get("properties", {})
    for prop in properties.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            text = "".join(part.get("plain_text", "") for part in title_parts)
            if text:
                return text
    return item.get("title", [{}])[0].get("plain_text", "Untitled") if item.get("title") else "Untitled"
