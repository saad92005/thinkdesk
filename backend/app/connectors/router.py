import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.connectors import google_oauth, notion_client, oauth_state, service, slack_oauth
from app.connectors.crypto import ConnectorEncryptionNotConfiguredError
from app.connectors.schemas import (
    AuthorizeUrlOut,
    ConnectNotionRequest,
    ConnectorOut,
    EmailMessageOut,
    NotionPageOut,
    SlackChannelOut,
)
from app.core.config import get_settings
from app.database import get_db
from app.models.connector import ConnectorProvider
from app.models.organization import OrganizationMember, OrganizationRole
from app.models.user import User
from app.organizations.dependencies import get_organization_membership
from app.organizations.service import get_membership

MANAGE_CONNECTORS_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}

router = APIRouter(tags=["connectors"])
org_router = APIRouter(prefix="/organizations/{organization_id}/connectors", tags=["connectors"])


async def _consume_state_or_403(db: AsyncSession, state: str, current_user: User) -> uuid.UUID:
    """Shared by every provider's callback: validates the CSRF state nonce,
    confirms it belongs to the user completing the flow, and confirms that
    user is still a member of the target organization. Returns the
    organization_id on success."""
    consumed = oauth_state.consume_state(state)
    if consumed is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This connection attempt has expired or was already used")

    organization_id, initiating_user_id = consumed
    if initiating_user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This connection attempt belongs to a different user")
    if await get_membership(db, organization_id, current_user.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this organization")
    return organization_id


@org_router.get("", response_model=list[ConnectorOut])
async def list_connectors_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[ConnectorOut]:
    accounts = await service.list_connections(db, organization_id)
    return [ConnectorOut.model_validate(a) for a in accounts]


@org_router.get("/google/authorize", response_model=AuthorizeUrlOut)
async def google_authorize_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
) -> AuthorizeUrlOut:
    if membership.role not in MANAGE_CONNECTORS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can connect integrations")

    try:
        nonce = oauth_state.create_state(organization_id, current_user.id)
        url = google_oauth.build_authorize_url(nonce)
    except google_oauth.GoogleOAuthNotConfiguredError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return AuthorizeUrlOut(authorize_url=url)


@org_router.get("/slack/authorize", response_model=AuthorizeUrlOut)
async def slack_authorize_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
) -> AuthorizeUrlOut:
    if membership.role not in MANAGE_CONNECTORS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can connect integrations")

    try:
        nonce = oauth_state.create_state(organization_id, current_user.id)
        url = slack_oauth.build_authorize_url(nonce)
    except slack_oauth.SlackOAuthNotConfiguredError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return AuthorizeUrlOut(authorize_url=url)


@org_router.post("/notion", response_model=ConnectorOut, status_code=status.HTTP_201_CREATED)
async def connect_notion_route(
    organization_id: uuid.UUID,
    payload: ConnectNotionRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConnectorOut:
    """Notion's internal-integration tokens aren't OAuth -- there's no
    authorize/callback dance, just a token the user pastes in from their
    own Notion integration settings. We still verify it against Notion's
    API before storing it, rather than trusting it blindly."""
    if membership.role not in MANAGE_CONNECTORS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can connect integrations")

    try:
        info = await notion_client.verify_token(payload.token)
    except notion_client.NotionTokenInvalidError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except notion_client.NotionError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    account = await service.upsert_connection(
        db,
        organization_id,
        current_user.id,
        ConnectorProvider.NOTION,
        info["label"],
        access_token=payload.token,
        refresh_token=None,
        expires_in=None,
        scopes="",
    )
    return ConnectorOut.model_validate(account)


@org_router.get("/{connector_id}/pages", response_model=list[NotionPageOut])
async def list_notion_pages_route(
    organization_id: uuid.UUID,
    connector_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[NotionPageOut]:
    account = await service.get_connection(db, organization_id, connector_id)
    if account is None or account.provider != ConnectorProvider.NOTION:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notion connector not found in this workspace")

    try:
        access_token = await service.get_valid_access_token(db, account)
        pages = await notion_client.search_pages(access_token)
    except (notion_client.NotionError, ConnectorEncryptionNotConfiguredError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not read Notion: {exc}")

    return [NotionPageOut(**p) for p in pages]


@org_router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector_route(
    organization_id: uuid.UUID,
    connector_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> None:
    if membership.role not in MANAGE_CONNECTORS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can remove integrations")

    deleted = await service.delete_connection(db, organization_id, connector_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connector not found in this workspace")


@org_router.get("/{connector_id}/emails", response_model=list[EmailMessageOut])
async def list_recent_emails_route(
    organization_id: uuid.UUID,
    connector_id: uuid.UUID,
    max_results: int = Query(default=10, ge=1, le=25),
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[EmailMessageOut]:
    account = await service.get_connection(db, organization_id, connector_id)
    if account is None or account.provider != ConnectorProvider.GOOGLE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gmail connector not found in this workspace")

    try:
        access_token = await service.get_valid_access_token(db, account)
        messages = await google_oauth.list_recent_messages(access_token, max_results=max_results)
    except (google_oauth.GoogleOAuthError, ConnectorEncryptionNotConfiguredError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not read Gmail: {exc}")

    return [
        EmailMessageOut(id=m["id"], subject=m["subject"], sender=m["from"], date=m["date"], snippet=m["snippet"])
        for m in messages
    ]


@org_router.get("/{connector_id}/channels", response_model=list[SlackChannelOut])
async def list_slack_channels_route(
    organization_id: uuid.UUID,
    connector_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[SlackChannelOut]:
    account = await service.get_connection(db, organization_id, connector_id)
    if account is None or account.provider != ConnectorProvider.SLACK:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slack connector not found in this workspace")

    try:
        access_token = await service.get_valid_access_token(db, account)
        channels = await slack_oauth.list_channels(access_token)
    except (slack_oauth.SlackOAuthError, ConnectorEncryptionNotConfiguredError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not read Slack channels: {exc}")

    return [SlackChannelOut(**c) for c in channels]


@router.get("/connectors/google/callback")
async def google_callback_route(
    code: str,
    state: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    organization_id = await _consume_state_or_403(db, state, current_user)

    try:
        tokens = await google_oauth.exchange_code_for_tokens(code)
        account_label = await google_oauth.fetch_user_email(tokens["access_token"])
        await service.upsert_connection(
            db,
            organization_id,
            current_user.id,
            ConnectorProvider.GOOGLE,
            account_label,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in"),
            scopes=tokens.get("scope", ""),
        )
    except (google_oauth.GoogleOAuthError, ConnectorEncryptionNotConfiguredError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Google connection failed: {exc}")

    frontend_url = get_settings().frontend_base_url
    return RedirectResponse(url=f"{frontend_url}/app/{organization_id}/connectors?connected=google")


@router.get("/connectors/slack/callback")
async def slack_callback_route(
    code: str,
    state: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    organization_id = await _consume_state_or_403(db, state, current_user)

    try:
        tokens = await slack_oauth.exchange_code_for_token(code)
        team_name = tokens.get("team", {}).get("name", "Slack workspace")
        await service.upsert_connection(
            db,
            organization_id,
            current_user.id,
            ConnectorProvider.SLACK,
            team_name,
            access_token=tokens["access_token"],
            refresh_token=None,
            expires_in=None,
            scopes=tokens.get("scope", ""),
        )
    except (slack_oauth.SlackOAuthError, ConnectorEncryptionNotConfiguredError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Slack connection failed: {exc}")

    frontend_url = get_settings().frontend_base_url
    return RedirectResponse(url=f"{frontend_url}/app/{organization_id}/connectors?connected=slack")
