import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import lemonsqueezy
from app.models.subscription import Subscription, SubscriptionStatus


class BillingError(Exception):
    """A checkout or webhook operation failed -- surfaced as a clear
    error, never silently swallowed."""


async def create_checkout(db: AsyncSession, organization_id: uuid.UUID, email: str) -> str:
    try:
        return await lemonsqueezy.create_checkout_url(organization_id, email)
    except (lemonsqueezy.LemonSqueezyNotConfiguredError, lemonsqueezy.LemonSqueezyError) as exc:
        raise BillingError(str(exc)) from exc


async def get_subscription(db: AsyncSession, organization_id: uuid.UUID) -> Subscription | None:
    return await db.scalar(select(Subscription).where(Subscription.organization_id == organization_id))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def apply_webhook_event(db: AsyncSession, event_name: str, custom_data: dict, data: dict) -> None:
    """Applies a Lemon Squeezy subscription webhook to our own Subscription
    table. This is the ONLY place a workspace's plan is ever changed --
    ThinkDesk never guesses or infers a plan change itself, it only
    reflects what Lemon Squeezy's signature-verified webhook actually says
    happened. Non-subscription events (orders, license keys, ...) are
    accepted and ignored rather than rejected, since Lemon Squeezy sends
    whatever event types the webhook is subscribed to.
    """
    if not event_name.startswith("subscription_"):
        return

    organization_id_raw = custom_data.get("organization_id")
    if not organization_id_raw:
        raise BillingError("Webhook event missing organization_id in custom_data")
    organization_id = uuid.UUID(organization_id_raw)

    attributes = data.get("attributes", {})
    subscription_id = str(data.get("id"))

    fields = dict(
        lemonsqueezy_subscription_id=subscription_id,
        lemonsqueezy_customer_id=str(attributes.get("customer_id")),
        variant_id=str(attributes.get("variant_id")),
        variant_name=attributes.get("variant_name", ""),
        status=SubscriptionStatus(attributes["status"]),
        renews_at=_parse_datetime(attributes.get("renews_at")),
        ends_at=_parse_datetime(attributes.get("ends_at")),
    )

    # Keyed by organization (one subscription per workspace), not by
    # Lemon Squeezy's subscription id -- a resubscribe after cancellation
    # gets a new subscription id but must still update the same row.
    existing = await db.scalar(select(Subscription).where(Subscription.organization_id == organization_id))
    if existing is not None:
        for key, value in fields.items():
            setattr(existing, key, value)
        await db.commit()
        return

    db.add(Subscription(organization_id=organization_id, **fields))
    await db.commit()
