import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.organization import OrganizationMember
from app.organizations.dependencies import get_organization_membership
from app.retrieval.schemas import SearchRequest, SearchResponse
from app.retrieval.service import search

router = APIRouter(prefix="/organizations/{organization_id}/search", tags=["retrieval"])


@router.post("", response_model=SearchResponse)
async def search_route(
    organization_id: uuid.UUID,
    payload: SearchRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    results = await search(db, organization_id, payload.query, payload.top_k)
    return SearchResponse(results=results)
