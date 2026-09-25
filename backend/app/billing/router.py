import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.billing import lemonsqueezy, limits, service
from app.billing.schemas import CheckoutResult, SubscriptionOut, UsageOut
from app.database import get_db
from app.models.organization import OrganizationMember, OrganizationRole
from app.models.user import User
from app.organizations.dependencies import get_organization_membership

MANAGE_BILLING_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}

org_router = APIRouter(prefix="/organizations/{organization_id}/billing", tags=["billing"])
router = APIRouter(tags=["billing"])


@org_router.post("/checkout", response_model=CheckoutResult)
async def create_checkout_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResult:
    if membership.role not in MANAGE_BILLING_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can manage billing")

    try:
        url = await service.create_checkout(db, organization_id, current_user.email)
    except service.BillingError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return CheckoutResult(checkout_url=url)


@org_router.get("/subscription", response_model=SubscriptionOut | None)
async def get_subscription_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut | None:
    subscription = await service.get_subscription(db, organization_id)
    if subscription is None:
        return None
    return SubscriptionOut.model_validate(subscription)


@org_router.get("/usage", response_model=UsageOut)
async def get_usage_route(
    organization_id: uuid.UUID,
    membership: OrganizationMember = Depends(get_organization_membership),
    db: AsyncSession = Depends(get_db),
) -> UsageOut:
    return UsageOut(**await limits.get_usage(db, organization_id))


@router.post("/billing/lemonsqueezy/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def lemonsqueezy_webhook_route(request: Request, db: AsyncSession = Depends(get_db)) -> None:
    # Signature is computed over the raw body -- must read it before any
    # JSON parsing touches it.
    raw_body = await request.body()
    signature = request.headers.get("X-Signature")
    if not lemonsqueezy.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature")

    payload = json.loads(raw_body)
    meta = payload.get("meta", {})

    try:
        await service.apply_webhook_event(db, meta.get("event_name", ""), meta.get("custom_data", {}), payload.get("data", {}))
    except service.BillingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
