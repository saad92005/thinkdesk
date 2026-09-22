import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.organization import OrganizationMember
from app.models.user import User
from app.organizations.dependencies import get_organization_membership
from app.organizations.schemas import MemberOut, OrganizationCreate, OrganizationOut
from app.organizations.service import create_organization, list_members, list_user_organizations

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationOut, status_code=201)
async def create_organization_route(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationOut:
    org = await create_organization(db, payload.name, current_user)
    return OrganizationOut.model_validate({**org.__dict__, "role": "owner"})


@router.get("", response_model=list[OrganizationOut])
async def list_organizations_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationOut]:
    orgs = await list_user_organizations(db, current_user)
    return [OrganizationOut.model_validate({**org.__dict__, "role": role}) for org, role in orgs]


@router.get("/{organization_id}/members", response_model=list[MemberOut])
async def list_members_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> list[MemberOut]:
    members = await list_members(db, organization_id)
    return [
        MemberOut.model_validate(
            {"user_id": user.id, "email": user.email, "role": member.role, "created_at": member.created_at}
        )
        for member, user in members
    ]
