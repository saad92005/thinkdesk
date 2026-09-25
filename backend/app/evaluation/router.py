import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.evaluation.schemas import EvalReport, EvalRunRequest
from app.evaluation.service import run_evaluation
from app.models.organization import OrganizationMember, OrganizationRole
from app.organizations.dependencies import get_organization_membership

# Running an eval burns LLM quota (a generation + a judge call per case),
# so it's gated like other workspace-management actions rather than open
# to every viewer.
EVAL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MANAGER}

router = APIRouter(prefix="/organizations/{organization_id}/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvalReport)
async def run_evaluation_route(
    organization_id: uuid.UUID,
    payload: EvalRunRequest,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> EvalReport:
    if membership.role not in EVAL_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners, admins, and managers can run evaluations")

    return await run_evaluation(db, organization_id, payload.cases)
