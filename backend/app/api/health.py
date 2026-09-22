from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.database import check_database_connection

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    database_ok = await check_database_connection()
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        database="connected" if database_ok else "unreachable",
        timestamp=datetime.now(timezone.utc),
    )
