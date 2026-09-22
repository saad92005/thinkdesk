from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, SignupRequest, UserOut
from app.auth.service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate,
    create_session,
    revoke_session,
    signup,
)
from app.core.config import get_settings
from app.database import get_db
from app.models.user import User
from app.organizations.service import create_organization

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup_route(payload: SignupRequest, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    try:
        user = await signup(db, payload.email, payload.password)
    except EmailAlreadyRegisteredError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    workspace_name = f"{payload.email.split('@')[0]}'s Workspace"
    await create_organization(db, workspace_name, user)

    token = await create_session(db, user)
    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserOut)
async def login_route(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    try:
        user = await authenticate(db, payload.email, payload.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = await create_session(db, user)
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_route(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token is not None:
        await revoke_session(db, token)
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=UserOut)
async def me_route(current_user: User = Depends(get_current_user)) -> User:
    return current_user
