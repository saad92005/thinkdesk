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


def _is_https_request(request: Request) -> bool:
    """Uvicorn sees plain HTTP from a local reverse proxy (ngrok, Vercel's
    edge, etc.) even when the browser's actual connection is HTTPS -- the
    proxy terminates TLS and forwards internally over HTTP, setting this
    header to say so."""
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    # A same-origin deployment (local dev, or the ngrok-proxies-everything
    # setup) works fine with Lax. A cross-origin deployment (a separate
    # frontend domain calling this backend directly, e.g. Vercel calling an
    # ngrok/Render backend) needs SameSite=None or the browser won't send
    # the cookie at all -- and SameSite=None requires Secure, which in turn
    # requires the request to actually be HTTPS. Basing this on the real
    # request rather than a static environment flag means the same backend
    # process correctly serves both local http://localhost dev and a public
    # HTTPS deployment without needing separate config for each.
    https = _is_https_request(request)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=https,
        samesite="none" if https else "lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup_route(
    payload: SignupRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> User:
    try:
        user = await signup(db, payload.email, payload.password)
    except EmailAlreadyRegisteredError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    workspace_name = f"{payload.email.split('@')[0]}'s Workspace"
    await create_organization(db, workspace_name, user)

    token = await create_session(db, user)
    _set_session_cookie(request, response, token)
    return user


@router.post("/login", response_model=UserOut)
async def login_route(
    payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> User:
    try:
        user = await authenticate(db, payload.email, payload.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = await create_session(db, user)
    _set_session_cookie(request, response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_route(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token is not None:
        await revoke_session(db, token)
    https = _is_https_request(request)
    response.delete_cookie(settings.session_cookie_name, path="/", secure=https, samesite="none" if https else "lax")


@router.get("/me", response_model=UserOut)
async def me_route(current_user: User = Depends(get_current_user)) -> User:
    return current_user
