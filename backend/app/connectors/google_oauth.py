from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

# Read-only: this connector reads email, it never sends or deletes on its
# own. A future "act on my inbox" agent action would need a broader scope
# and, per the project's own rule, a human-approval step before anything
# irreversible (sending, deleting) actually executes.
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
USERINFO_SCOPE = "https://www.googleapis.com/auth/userinfo.email"


class GoogleOAuthNotConfiguredError(Exception):
    """No GOOGLE_CLIENT_ID/SECRET configured."""


class GoogleOAuthError(Exception):
    """A call to Google's OAuth or Gmail API failed."""


def _require_settings():
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleOAuthNotConfiguredError(
            "Google OAuth isn't configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env."
        )
    return settings


def build_authorize_url(state: str) -> str:
    settings = _require_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": f"{GMAIL_SCOPE} {USERINFO_SCOPE}",
        "access_type": "offline",
        # Forces Google to always hand back a refresh_token, even if this
        # user connected before -- without it, a re-connect after the
        # first time silently omits refresh_token.
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    settings = _require_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
        )
    if response.status_code != 200:
        raise GoogleOAuthError(f"Token exchange failed: {response.text}")
    return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    settings = _require_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code != 200:
        raise GoogleOAuthError(f"Token refresh failed: {response.text}")
    return response.json()


async def fetch_user_email(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code != 200:
        raise GoogleOAuthError(f"Fetching account email failed: {response.text}")
    return response.json()["email"]


async def list_recent_messages(access_token: str, max_results: int = 10) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        list_response = await client.get(
            GMAIL_MESSAGES_URL, headers=headers, params={"maxResults": max_results}
        )
        if list_response.status_code != 200:
            raise GoogleOAuthError(f"Listing messages failed: {list_response.text}")

        message_ids = [m["id"] for m in list_response.json().get("messages", [])]
        messages = []
        for message_id in message_ids:
            detail_response = await client.get(
                f"{GMAIL_MESSAGES_URL}/{message_id}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
            )
            if detail_response.status_code != 200:
                continue
            detail = detail_response.json()
            header_map = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            messages.append(
                {
                    "id": message_id,
                    "subject": header_map.get("Subject", "(no subject)"),
                    "from": header_map.get("From", "(unknown sender)"),
                    "date": header_map.get("Date", ""),
                    "snippet": detail.get("snippet", ""),
                }
            )
        return messages
