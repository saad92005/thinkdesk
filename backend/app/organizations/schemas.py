import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.organization import OrganizationRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class MemberInvite(BaseModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    role: OrganizationRole


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    role: OrganizationRole
    created_at: datetime
