from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.core.config import get_settings
from app.documents.router import router as documents_router
from app.evaluation.router import router as evaluation_router
from app.intelligence.router import router as intelligence_router
from app.organizations.router import router as organizations_router
from app.research.router import router as research_router
from app.retrieval.router import router as retrieval_router

settings = get_settings()

app = FastAPI(
    title="ThinkDesk API",
    description=(
        "AI knowledge workspace API: multi-tenant document ingestion, hybrid "
        "(vector + BM25) retrieval, and grounded chat with real citations. "
        "Authorization is enforced at the organization-membership layer "
        "before any document or chunk is ever read."
    ),
    version="0.2.0",
    contact={"name": "ThinkDesk"},
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
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(evaluation_router)
app.include_router(intelligence_router)
app.include_router(research_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "thinkdesk-api", "status": "running"}
