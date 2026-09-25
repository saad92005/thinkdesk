from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.access"
CONVERSATIONS_LIST_URL = "https://slack.com/api/conversations.list"

# Read-only-equivalent: this connector lists channels, it never posts on
# its own. A future "post an update" agent action would need chat:write
# used for an actual send, plus, per the project's own rule, a human
# approval step before that message actually goes out.
BOT_SCOPES = "channels:read"


class SlackOAuthNotConfiguredError(Exception):
    """No SLACK_CLIENT_ID/SECRET configured."""


class SlackOAuthError(Exception):
    """A call to Slack's OAuth or Web API failed."""


def _require_settings():
    settings = get_settings()
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise SlackOAuthNotConfiguredError(
            "Slack OAuth isn't configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET in backend/.env."
        )
    return settings


def build_authorize_url(state: str) -> str:
    settings = _require_settings()
    params = {
        "client_id": settings.slack_client_id,
        "redirect_uri": settings.slack_redirect_uri,
        "scope": BOT_SCOPES,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    settings = _require_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "code": code,
                "redirect_uri": settings.slack_redirect_uri,
            },
        )
    body = response.json()
    if response.status_code != 200 or not body.get("ok"):
        raise SlackOAuthError(f"Token exchange failed: {body.get('error', response.text)}")
    return body


async def list_channels(access_token: str, limit: int = 20) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            CONVERSATIONS_LIST_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": limit, "types": "public_channel"},
        )
    body = response.json()
    if response.status_code != 200 or not body.get("ok"):
        raise SlackOAuthError(f"Listing channels failed: {body.get('error', response.text)}")

    return [
        {
            "id": c["id"],
            "name": c["name"],
            "is_member": c.get("is_member", False),
            "num_members": c.get("num_members"),
        }
        for c in body.get("channels", [])
    ]
