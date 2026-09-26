import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation import service
from app.automation.schemas import AutomationRuleOut, CreateAutomationRuleRequest, QueuedDraftOut
from app.database import get_db
from app.models.organization import OrganizationMember, OrganizationRole
from app.organizations.dependencies import get_organization_membership

# Same split as app/agents/: creating/running a rule only ever produces a
# queued draft (no external effect), so it's open to any member. Approving
# a queued draft is the only write, gated the same way post-to-slack is.
EXECUTE_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}

router = APIRouter(prefix="/organizations/{organization_id}/automations", tags=["automation"])


@router.post("", response_model=AutomationRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule_route(
    organization_id: uuid.UUID,
    payload: CreateAutomationRuleRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> AutomationRuleOut:
    try:
        rule = await service.create_rule(
            db,
            organization_id,
            payload.name,
            payload.source,
            payload.gmail_connector_id,
            payload.document_id,
            payload.slack_connector_id,
            payload.channel_id,
        )
    except service.AutomationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return AutomationRuleOut.model_validate(rule)


@router.get("", response_model=list[AutomationRuleOut])
async def list_rules_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[AutomationRuleOut]:
    rules = await service.list_rules(db, organization_id)
    return [AutomationRuleOut.model_validate(r) for r in rules]


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_route(
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await service.delete_rule(db, organization_id, rule_id)
    except service.AutomationError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.post("/{rule_id}/run", response_model=QueuedDraftOut)
async def run_rule_route(
    organization_id: uuid.UUID,
    rule_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> QueuedDraftOut:
    try:
        queued = await service.run_rule(db, organization_id, rule_id)
    except service.AutomationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return QueuedDraftOut.model_validate(queued)


@router.get("/queue", response_model=list[QueuedDraftOut])
async def list_queue_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[QueuedDraftOut]:
    queue = await service.list_queue(db, organization_id)
    return [QueuedDraftOut.model_validate(q) for q in queue]


class ApproveQueuedDraftRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


@router.post("/queue/{draft_id}/approve")
async def approve_queued_draft_route(
    organization_id: uuid.UUID,
    draft_id: uuid.UUID,
    payload: ApproveQueuedDraftRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if membership.role not in EXECUTE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can approve and send")
    try:
        ts = await service.approve_queued_draft(db, organization_id, draft_id, payload.message)
    except service.AutomationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return {"posted": True, "slack_ts": ts}


@router.post("/queue/{draft_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_queued_draft_route(
    organization_id: uuid.UUID,
    draft_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await service.dismiss_queued_draft(db, organization_id, draft_id)
    except service.AutomationError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
