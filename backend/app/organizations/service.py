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
