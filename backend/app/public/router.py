from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.session import get_session
from app.identity.entitlements import resolve_entitlements
from app.identity.models import Plan, Tenant
from app.identity.service import get_plan, get_tenant_by_domain, get_tenant_by_slug

router = APIRouter()


class TenantPublic(BaseModel):
    slug: str
    name: str
    status: str
    branding: dict[str, Any]
    locale: str
    currency: str
    timezone: str
    plan_code: str
    features: dict[str, bool]


class PlanPublic(BaseModel):
    code: str
    name: str
    description: str
    price_cents: int
    currency: str
    interval: str
    features: dict[str, Any]
    quotas: dict[str, Any]
    sort_order: int


@router.get("/tenant", response_model=TenantPublic)
async def resolve_tenant(
    slug: str | None = None,
    domain: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    if not slug and not domain:
        raise AppError("Provide a workspace slug or custom domain.")

    tenant: Tenant | None = None
    if domain:
        tenant = await get_tenant_by_domain(db, domain)
    if tenant is None and slug:
        tenant = await get_tenant_by_slug(db, slug)
    if tenant is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Workspace not found.")

    plan = await get_plan(db, tenant.plan_code)
    entitlements = resolve_entitlements(
        plan.features if plan else {},
        plan.quotas if plan else {},
        tenant.features_override,
    )
    return TenantPublic(
        slug=tenant.slug,
        name=tenant.name,
        status=tenant.status,
        branding=tenant.branding or {},
        locale=tenant.locale,
        currency=tenant.default_currency,
        timezone=tenant.timezone,
        plan_code=tenant.plan_code,
        features=entitlements.features,
    )


@router.get("/plans", response_model=list[PlanPublic])
async def list_public_plans(
    limit: int = Query(10, ge=1, le=30),
    db: AsyncSession = Depends(get_session),
):
    plans = (
        await db.execute(
            select(Plan)
            .where(Plan.is_active.is_(True))
            .order_by(Plan.sort_order.asc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        PlanPublic(
            code=p.code,
            name=p.name,
            description=p.description,
            price_cents=p.price_cents,
            currency=p.currency,
            interval=p.interval,
            features=p.features,
            quotas=p.quotas,
            sort_order=p.sort_order,
        )
        for p in plans
    ]
