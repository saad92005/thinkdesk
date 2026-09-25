import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import google_oauth
from app.connectors.crypto import decrypt, encrypt
from app.models.connector import ConnectorAccount, ConnectorProvider


async def upsert_google_connection(
    db: AsyncSession,
    organization_id: uuid.UUID,
    connected_by_user_id: uuid.UUID,
    account_email: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    scopes: str,
) -> ConnectorAccount:
    existing = await db.scalar(
        select(ConnectorAccount).where(
            ConnectorAccount.organization_id == organization_id,
            ConnectorAccount.provider == ConnectorProvider.GOOGLE,
            ConnectorAccount.account_email == account_email,
        )
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None

    if existing is not None:
        existing.access_token_encrypted = encrypt(access_token)
        if refresh_token:
            existing.refresh_token_encrypted = encrypt(refresh_token)
        existing.token_expires_at = expires_at
        existing.scopes = scopes
        existing.connected_by_user_id = connected_by_user_id
        await db.commit()
        await db.refresh(existing)
        return existing

    account = ConnectorAccount(
        organization_id=organization_id,
        connected_by_user_id=connected_by_user_id,
        provider=ConnectorProvider.GOOGLE,
        account_email=account_email,
        access_token_encrypted=encrypt(access_token),
        refresh_token_encrypted=encrypt(refresh_token) if refresh_token else None,
        token_expires_at=expires_at,
        scopes=scopes,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def list_connections(db: AsyncSession, organization_id: uuid.UUID) -> list[ConnectorAccount]:
    result = await db.execute(
        select(ConnectorAccount)
        .where(ConnectorAccount.organization_id == organization_id)
        .order_by(ConnectorAccount.created_at)
    )
    return list(result.scalars().all())


async def get_connection(
    db: AsyncSession, organization_id: uuid.UUID, connector_id: uuid.UUID
) -> ConnectorAccount | None:
    return await db.scalar(
        select(ConnectorAccount).where(
            ConnectorAccount.id == connector_id, ConnectorAccount.organization_id == organization_id
        )
    )


async def delete_connection(db: AsyncSession, organization_id: uuid.UUID, connector_id: uuid.UUID) -> bool:
    account = await get_connection(db, organization_id, connector_id)
    if account is None:
        return False
    await db.delete(account)
    await db.commit()
    return True


async def get_valid_access_token(db: AsyncSession, account: ConnectorAccount) -> str:
    """Returns a usable access token, transparently refreshing it first if
    it's expired (or about to expire within 60s) and a refresh token is on
    file. Falls back to the stored (possibly stale) token if there's no
    refresh token to renew it with, rather than raising -- the caller's own
    API call will surface a clear 401 from Google if it's truly expired."""
    now = datetime.now(timezone.utc)
    if account.token_expires_at is None or account.token_expires_at > now + timedelta(seconds=60):
        return decrypt(account.access_token_encrypted)

    if not account.refresh_token_encrypted:
        return decrypt(account.access_token_encrypted)

    refreshed = await google_oauth.refresh_access_token(decrypt(account.refresh_token_encrypted))
    account.access_token_encrypted = encrypt(refreshed["access_token"])
    if refreshed.get("expires_in"):
        account.token_expires_at = now + timedelta(seconds=refreshed["expires_in"])
    await db.commit()
    return refreshed["access_token"]
