from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.subscription import SubscriptionStatus


class CheckoutResult(BaseModel):
    checkout_url: str


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: SubscriptionStatus
    variant_name: str
    renews_at: datetime | None
    ends_at: datetime | None


class UsageOut(BaseModel):
    is_paid_plan: bool
    document_count: int
    document_limit: int | None
    message_count: int
    message_limit: int | None
