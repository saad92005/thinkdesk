import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.connector import ConnectorProvider


class ConnectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: ConnectorProvider
    account_label: str
    created_at: datetime


class AuthorizeUrlOut(BaseModel):
    authorize_url: str


class EmailMessageOut(BaseModel):
    id: str
    subject: str
    sender: str
    date: str
    snippet: str


class SlackChannelOut(BaseModel):
    id: str
    name: str
    is_member: bool
    num_members: int | None
