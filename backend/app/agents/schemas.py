import uuid

from pydantic import BaseModel, Field


class DraftEmailSummaryRequest(BaseModel):
    gmail_connector_id: uuid.UUID
    max_results: int = Field(default=10, ge=1, le=25)


class DraftEmailSummaryResult(BaseModel):
    draft_text: str
    source_email_count: int


class PostToSlackRequest(BaseModel):
    slack_connector_id: uuid.UUID
    channel_id: str
    # The human-approved text to actually post -- may differ from whatever
    # draft_text a prior /draft-email-summary call returned, since the
    # human is free to edit it before approving. This endpoint has no idea
    # a draft ever existed; it only knows it was told to post this exact
    # text, by someone with permission to do so.
    message: str = Field(min_length=1, max_length=4000)


class PostToSlackResult(BaseModel):
    posted: bool
    channel_id: str
    slack_ts: str
