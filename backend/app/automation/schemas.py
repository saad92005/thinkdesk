import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.automation import AutomationSource, QueuedDraftStatus


class CreateAutomationRuleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source: AutomationSource
    gmail_connector_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    slack_connector_id: uuid.UUID
    channel_id: str = Field(min_length=1, max_length=64)


class AutomationRuleOut(BaseModel):
    id: uuid.UUID
    name: str
    source: AutomationSource
    gmail_connector_id: uuid.UUID | None
    document_id: uuid.UUID | None
    slack_connector_id: uuid.UUID
    channel_id: str
    active: bool
    last_run_at: datetime | None

    class Config:
        from_attributes = True


class QueuedDraftOut(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    rule_name: str
    draft_text: str
    source_label: str
    slack_connector_id: uuid.UUID
    channel_id: str
    status: QueuedDraftStatus
    created_at: datetime

    class Config:
        from_attributes = True
