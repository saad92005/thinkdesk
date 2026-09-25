import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.service import get_subscription
from app.models.document import Document
from app.models.message import Conversation, Message, MessageRole
from app.models.subscription import SubscriptionStatus

# Deliberately small, real numbers -- not a marketing "unlimited" that
# quietly never gets enforced. A workspace with an active/trialing
# subscription skips these entirely.
FREE_DOCUMENT_LIMIT = 3
FREE_MESSAGE_LIMIT = 50

_PAID_STATUSES = {SubscriptionStatus.ACTIVE, SubscriptionStatus.ON_TRIAL}


class UsageLimitError(Exception):
    """A free-plan limit was hit. The message is safe to show the user
    directly -- it names the limit and points at the upgrade path."""


async def is_on_paid_plan(db: AsyncSession, organization_id: uuid.UUID) -> bool:
    subscription = await get_subscription(db, organization_id)
    return subscription is not None and subscription.status in _PAID_STATUSES


async def _count_documents(db: AsyncSession, organization_id: uuid.UUID) -> int:
    return await db.scalar(
        select(func.count()).select_from(Document).where(Document.organization_id == organization_id)
    )


async def _count_messages(db: AsyncSession, organization_id: uuid.UUID) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.organization_id == organization_id, Message.role == MessageRole.USER)
    )


async def get_usage(db: AsyncSession, organization_id: uuid.UUID) -> dict:
    """Powers the billing page's usage card -- computed with the same
    counting functions the enforcement checks below use, so what's
    displayed can never drift from what's actually enforced."""
    paid = await is_on_paid_plan(db, organization_id)
    return {
        "is_paid_plan": paid,
        "document_count": await _count_documents(db, organization_id),
        "document_limit": None if paid else FREE_DOCUMENT_LIMIT,
        "message_count": await _count_messages(db, organization_id),
        "message_limit": None if paid else FREE_MESSAGE_LIMIT,
    }


async def enforce_document_limit(db: AsyncSession, organization_id: uuid.UUID) -> None:
    if await is_on_paid_plan(db, organization_id):
        return
    if await _count_documents(db, organization_id) >= FREE_DOCUMENT_LIMIT:
        raise UsageLimitError(
            f"The free plan is limited to {FREE_DOCUMENT_LIMIT} documents per workspace. "
            "Upgrade to Pro for unlimited uploads."
        )


async def enforce_message_limit(db: AsyncSession, organization_id: uuid.UUID) -> None:
    if await is_on_paid_plan(db, organization_id):
        return
    if await _count_messages(db, organization_id) >= FREE_MESSAGE_LIMIT:
        raise UsageLimitError(
            f"The free plan is limited to {FREE_MESSAGE_LIMIT} chat messages per workspace. "
            "Upgrade to Pro for unlimited chat."
        )
