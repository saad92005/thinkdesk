from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.core.config import get_settings
from app.models.session import Session
from app.models.user import User

settings = get_settings()


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def signup(db: AsyncSession, email: str, password: str) -> User:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    return user


async def create_session(db: AsyncSession, user: User) -> str:
    token = generate_session_token()
    session = Session(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
    )
    db.add(session)
    await db.commit()
    return token


async def get_user_from_token(db: AsyncSession, token: str) -> User | None:
    token_hash = hash_session_token(token)
    session = await db.scalar(
        select(Session).where(
            Session.token_hash == token_hash,
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    if session is None:
        return None
    return await db.get(User, session.user_id)


async def revoke_session(db: AsyncSession, token: str) -> None:
    token_hash = hash_session_token(token)
    await db.execute(delete(Session).where(Session.token_hash == token_hash))
    await db.commit()
