"""Provider-agnostic billing sync.

Verified principle (Stripe guidance, 2026 writeups): billing is the provider's
job, ENTITLEMENTS are ours. This module keeps the local subscription state
(tenant.plan_code, billing_customer_id) in sync from provider webhooks; every
request-time enforcement reads the local state, never the provider.

The Stripe webhook implements the documented signature scheme (HMAC-SHA256 of
"{timestamp}.{payload}") with a 5-minute tolerance and event idempotency via
audit_log.
"""

import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog
from app.audit.service import record_audit
from app.core.config import settings
from app.core.errors import AppError, AuthError, NotConfiguredError, NotFoundError
from app.db.rls import set_tenant_context
from app.db.session import get_session
from app.identity.dependencies import AuthContext, get_current_context
from app.identity.models import Tenant
from app.identity.plans import DEFAULT_PLAN_CODE
from app.identity.service import get_plan, get_tenant_by_slug

router = APIRouter()

SUBSCRIPTION_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "checkout.session.completed",
}


class SubscriptionOut(BaseModel):
    plan_code: str
    plan_name: str
    status: str
    trial_ends_at: str | None
    billing_customer_id: str | None
    features: dict[str, Any]
    quotas: dict[str, Any]


def _verify_stripe_signature(payload: bytes, header: str, secret: str) -> bool:
    parts: dict[str, str] = {}
    for item in header.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts[key.strip()] = value.strip()
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    signed_payload = f"{timestamp}.{payload.decode('utf-8', errors='replace')}"
    expected = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _resolve_tenant(
    db: AsyncSession, tenant_slug: str | None, customer_id: str | None
) -> Tenant | None:
    tenant: Tenant | None = None
    if tenant_slug:
        tenant = await get_tenant_by_slug(db, tenant_slug)
    if tenant is None and customer_id:
        result = await db.execute(
            select(Tenant).where(Tenant.billing_customer_id == customer_id)
        )
        tenant = result.scalar_one_or_none()
    return tenant


async def _apply_event(db: AsyncSession, event: dict[str, Any]) -> dict[str, Any]:
    event_id = str(event.get("id", ""))
    event_type = str(event.get("type", ""))
    data = (event.get("data") or {}).get("object") or {}
    metadata = data.get("metadata") or {}
    tenant_slug = metadata.get("tenant_slug")
    plan_code = metadata.get("plan_code")
    customer_id = data.get("customer")

    if event_type not in SUBSCRIPTION_EVENTS:
        return {"received": True, "ignored": True, "type": event_type}

    tenant = await _resolve_tenant(db, tenant_slug, customer_id)
    if tenant is None:
        return {"received": True, "ignored": True, "reason": "tenant_not_mapped"}

    await set_tenant_context(db, tenant.id)

    if event_id:
        duplicate = (
            await db.execute(
                select(AuditLog.id).where(
                    AuditLog.tenant_id == tenant.id,
                    AuditLog.action == "billing.webhook",
                    AuditLog.entity_id == event_id,
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            return {"received": True, "duplicate": True}

    if event_type == "customer.subscription.deleted":
        tenant.plan_code = DEFAULT_PLAN_CODE
    else:
        if plan_code and await get_plan(db, str(plan_code)):
            tenant.plan_code = str(plan_code)
    if customer_id:
        tenant.billing_customer_id = str(customer_id)

    await record_audit(
        db,
        tenant_id=tenant.id,
        actor_id=None,
        actor_email="billing-webhook",
        action="billing.webhook",
        entity_type="stripe_event",
        entity_id=event_id,
        payload={"type": event_type, "plan_code": tenant.plan_code},
    )
    return {"received": True, "tenant": tenant.slug, "plan_code": tenant.plan_code}


@router.get("/subscription", response_model=SubscriptionOut)
async def subscription(
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
):
    from app.identity.entitlements import resolve_entitlements

    plan = await get_plan(db, ctx.tenant.plan_code)
    entitlements = resolve_entitlements(
        plan.features if plan else {},
        plan.quotas if plan else {},
        ctx.tenant.features_override,
    )
    return SubscriptionOut(
        plan_code=ctx.tenant.plan_code,
        plan_name=plan.name if plan else ctx.tenant.plan_code,
        status=ctx.tenant.status,
        trial_ends_at=ctx.tenant.trial_ends_at.isoformat() if ctx.tenant.trial_ends_at else None,
        billing_customer_id=ctx.tenant.billing_customer_id,
        features=entitlements.features,
        quotas=entitlements.quotas,
    )


@router.post("/webhook/{provider}")
async def billing_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    if provider != "stripe":
        raise NotFoundError("Unknown billing provider.")

    secret = settings.stripe_webhook_secret
    if not secret:
        raise NotConfiguredError("Billing webhooks are not configured on this deployment.")

    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    if not _verify_stripe_signature(payload, signature, secret):
        raise AuthError("Invalid webhook signature.")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AppError("Invalid webhook payload.") from exc
    if not isinstance(event, dict):
        raise AppError("Invalid webhook payload.")

    return await _apply_event(db, event)
