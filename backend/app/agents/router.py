import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import service
from app.agents.schemas import (
    DraftDocumentDigestRequest,
    DraftDocumentDigestResult,
    DraftEmailSummaryRequest,
    DraftEmailSummaryResult,
    PostToSlackRequest,
    PostToSlackResult,
)
from app.database import get_db
from app.models.organization import OrganizationMember, OrganizationRole
from app.organizations.dependencies import get_organization_membership

# Drafting is read-only (open to any member, like chat/search). Actually
# posting to a real, external Slack workspace on the org's behalf is
# gated the same way other write-ish workspace actions are.
EXECUTE_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}

router = APIRouter(prefix="/organizations/{organization_id}/agent", tags=["agent"])


@router.post("/draft-email-summary", response_model=DraftEmailSummaryResult)
async def draft_email_summary_route(
    organization_id: uuid.UUID,
    payload: DraftEmailSummaryRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> DraftEmailSummaryResult:
    try:
        draft_text, count = await service.draft_email_summary(
            db, organization_id, payload.gmail_connector_id, payload.max_results
        )
    except service.AgentActionError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return DraftEmailSummaryResult(draft_text=draft_text, source_email_count=count)


@router.post("/draft-document-digest", response_model=DraftDocumentDigestResult)
async def draft_document_digest_route(
    organization_id: uuid.UUID,
    payload: DraftDocumentDigestRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> DraftDocumentDigestResult:
    try:
        draft_text, filename, truncated = await service.draft_document_digest(
            db, organization_id, payload.document_id
        )
    except service.AgentActionError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return DraftDocumentDigestResult(draft_text=draft_text, source_document_name=filename, truncated=truncated)


@router.post("/post-to-slack", response_model=PostToSlackResult)
async def post_to_slack_route(
    organization_id: uuid.UUID,
    payload: PostToSlackRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> PostToSlackResult:
    if membership.role not in EXECUTE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can post to Slack from here")

    try:
        ts = await service.post_to_slack(
            db, organization_id, payload.slack_connector_id, payload.channel_id, payload.message
        )
    except service.AgentActionError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return PostToSlackResult(posted=True, channel_id=payload.channel_id, slack_ts=ts)
