import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.intelligence.schemas import ComparisonRequest, ComparisonResult, ExtractionResult, ReportRequest, ReportResult
from app.intelligence.service import (
    ComparisonUnavailableError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    ExtractionUnavailableError,
    ReportUnavailableError,
    compare_documents,
    extract_key_information,
    generate_report,
)
from app.models.organization import OrganizationMember
from app.organizations.dependencies import get_organization_membership

router = APIRouter(prefix="/organizations/{organization_id}/documents", tags=["intelligence"])


@router.post("/compare", response_model=ComparisonResult)
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


@router.post("/{document_id}/extract", response_model=ExtractionResult)
async def extract_document_route(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResult:
    try:
        return await extract_key_information(db, organization_id, document_id)
    except DocumentNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That document wasn't found in this workspace")
    except DocumentNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"'{exc}' hasn't finished processing yet")
    except ExtractionUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Extraction unavailable: {exc}")


@router.post("/report", response_model=ReportResult)
async def generate_report_route(
    organization_id: uuid.UUID,
    payload: ReportRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> ReportResult:
    try:
        return await generate_report(db, organization_id, payload.document_ids, payload.focus)
    except DocumentNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "One or more documents were not found in this workspace")
    except DocumentNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"'{exc}' hasn't finished processing yet")
    except ReportUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Report generation unavailable: {exc}")
