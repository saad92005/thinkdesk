import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.intelligence.schemas import ComparisonRequest, ComparisonResult
from app.intelligence.service import (
    ComparisonUnavailableError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    compare_documents,
)
from app.models.organization import OrganizationMember
from app.organizations.dependencies import get_organization_membership

router = APIRouter(prefix="/organizations/{organization_id}/documents/compare", tags=["intelligence"])


@router.post("", response_model=ComparisonResult)
async def compare_documents_route(
    organization_id: uuid.UUID,
    payload: ComparisonRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> ComparisonResult:
    if payload.document_id_a == payload.document_id_b:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose two different documents to compare")

    try:
        return await compare_documents(db, organization_id, payload.document_id_a, payload.document_id_b)
    except DocumentNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "One or both documents were not found in this workspace")
    except DocumentNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"'{exc}' hasn't finished processing yet")
    except ComparisonUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Comparison unavailable: {exc}")
