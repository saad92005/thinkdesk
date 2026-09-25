import re
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.user import User


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
    return f"{base}-{secrets.token_hex(3)}"


async def create_organization(db: AsyncSession, name: str, owner: User) -> Organization:
    org = Organization(name=name, slug=_slugify(name))
    db.add(org)
    await db.flush()

    membership = OrganizationMember(organization_id=org.id, user_id=owner.id, role=OrganizationRole.OWNER)
    db.add(membership)
    await db.commit()
    await db.refresh(org)
    return org


async def list_user_organizations(db: AsyncSession, user: User) -> list[tuple[Organization, OrganizationRole]]:
    result = await db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
        .order_by(Organization.created_at)
    )
    return [(org, role) for org, role in result.all()]


async def get_membership(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> OrganizationMember | None:
    return await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )


async def list_members(db: AsyncSession, organization_id: uuid.UUID) -> list[tuple[OrganizationMember, User]]:
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.created_at)
    )
    return [(member, user) for member, user in result.all()]


class UserNotFoundError(Exception):
    """No account exists with the given email. There's no email-sending
    infrastructure (Phase 7, blocked on real provider credentials), so
    invites only work for people who already have a ThinkDesk account --
    an honest limitation, not a silently broken invite flow."""


class AlreadyMemberError(Exception):
    pass


async def add_member(
    db: AsyncSession, organization_id: uuid.UUID, email: str, role: OrganizationRole
) -> tuple[OrganizationMember, User]:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise UserNotFoundError(email)

    if await get_membership(db, organization_id, user.id) is not None:
        raise AlreadyMemberError(email)

    member = OrganizationMember(organization_id=organization_id, user_id=user.id, role=role)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member, user


class LastOwnerError(Exception):
    """Raised when demoting or removing a member would leave the
    organization with zero owners -- there must always be someone who can
    manage it, so this is blocked rather than silently allowed."""


async def _count_owners(db: AsyncSession, organization_id: uuid.UUID) -> int:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == OrganizationRole.OWNER,
        )
    )
    return len(result.scalars().all())


async def update_member_role(
    db: AsyncSession, organization_id: uuid.UUID, target_user_id: uuid.UUID, new_role: OrganizationRole
) -> OrganizationMember | None:
    member = await get_membership(db, organization_id, target_user_id)
    if member is None:
        return None

    if member.role == OrganizationRole.OWNER and new_role != OrganizationRole.OWNER:
        if await _count_owners(db, organization_id) <= 1:
            raise LastOwnerError()

    member.role = new_role
    await db.commit()
    await db.refresh(member)
    return member


async def remove_member(db: AsyncSession, organization_id: uuid.UUID, target_user_id: uuid.UUID) -> bool:
    member = await get_membership(db, organization_id, target_user_id)
    if member is None:
        return False

    if member.role == OrganizationRole.OWNER and await _count_owners(db, organization_id) <= 1:
        raise LastOwnerError()

    await db.delete(member)
    await db.commit()
    return True
