import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.organization import OrganizationMember
from app.organizations.dependencies import get_organization_membership
from app.research.schemas import ResearchReport, ResearchRequest
from app.research.service import ResearchUnavailableError, research_topic

router = APIRouter(prefix="/organizations/{organization_id}/research", tags=["research"])


@router.post("", response_model=ResearchReport)
async def research_topic_route(
    organization_id: uuid.UUID,
    payload: ResearchRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> ResearchReport:
    try:
        return await research_topic(db, organization_id, payload.topic)
    except ResearchUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Research unavailable: {exc}")
