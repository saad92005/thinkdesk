import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.organization import OrganizationMember
from app.models.user import User
from app.organizations.service import get_membership


async def get_organization_membership(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMember:
    """Authorization gate: every organization-scoped route depends on this.

    This runs before any document/knowledge lookup, so a user who isn't a
    member of the organization never reaches the retrieval layer at all —
    the LLM is never in a position to leak data across tenants because the
    data itself is never fetched.
    """
    membership = await get_membership(db, organization_id, current_user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    return membership
