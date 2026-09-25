import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.organization import OrganizationMember, OrganizationRole
from app.models.user import User
from app.organizations.dependencies import get_organization_membership
from app.organizations.schemas import MemberInvite, MemberOut, MemberRoleUpdate, OrganizationCreate, OrganizationOut
from app.organizations.service import (
    AlreadyMemberError,
    LastOwnerError,
    UserNotFoundError,
    add_member,
    create_organization,
    list_members,
    list_user_organizations,
    remove_member,
    update_member_role,
)

MANAGE_MEMBERS_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}

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


@router.post("/{organization_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member_route(
    organization_id: uuid.UUID,
    payload: MemberInvite,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    if membership.role not in MANAGE_MEMBERS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can add members")

    try:
        member, user = await add_member(db, organization_id, payload.email, payload.role)
    except UserNotFoundError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No ThinkDesk account exists with that email yet -- they need to sign up first",
        )
    except AlreadyMemberError:
        raise HTTPException(status.HTTP_409_CONFLICT, "This person is already a member of this workspace")

    return MemberOut.model_validate(
        {"user_id": user.id, "email": user.email, "role": member.role, "created_at": member.created_at}
    )


@router.patch("/{organization_id}/members/{user_id}", response_model=MemberOut)
async def update_member_role_route(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    if membership.role not in MANAGE_MEMBERS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can change member roles")

    try:
        member = await update_member_role(db, organization_id, user_id, payload.role)
    except LastOwnerError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An organization must always have at least one owner")

    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That user isn't a member of this organization")

    user = await db.get(User, user_id)
    return MemberOut.model_validate(
        {"user_id": user.id, "email": user.email, "role": member.role, "created_at": member.created_at}
    )


@router.delete("/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member_route(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    is_self = user_id == current_user.id
    if not is_self and membership.role not in MANAGE_MEMBERS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can remove other members")

    try:
        removed = await remove_member(db, organization_id, user_id)
    except LastOwnerError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An organization must always have at least one owner")

    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That user isn't a member of this organization")
