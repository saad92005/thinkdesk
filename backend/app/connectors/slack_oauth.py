from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.access"
CONVERSATIONS_LIST_URL = "https://slack.com/api/conversations.list"
POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"

# chat:write enables post_message() below -- used only by the agent
# action's send step (app/agents/service.py::post_to_slack), which is
# reached only after a human explicitly approves the drafted text. Slack
# wants a comma-separated scope list, unlike Google's space-separated one.
BOT_SCOPES = "channels:read,chat:write"


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


async def post_message(access_token: str, channel: str, text: str) -> dict:
    """The only place this codebase ever writes to Slack. Callers must
    only reach this after a human has explicitly approved `text` -- see
    app/agents/router.py's post-to-slack route, which is the sole caller."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            POST_MESSAGE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"channel": channel, "text": text},
        )
    body = response.json()
    if response.status_code != 200 or not body.get("ok"):
        raise SlackOAuthError(f"Posting message failed: {body.get('error', response.text)}")
    return body
