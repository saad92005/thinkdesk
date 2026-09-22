from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.organizations.router import router as organizations_router

settings = get_settings()

app = FastAPI(
    title="ThinkDesk API",
    description="Your knowledge. Your AI workspace.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organizations_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "thinkdesk-api", "status": "running"}
