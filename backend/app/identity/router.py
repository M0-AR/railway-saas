import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, clamp_page
from app.core.request import client_ip
from app.db.session import get_session
from app.identity import service
from app.identity.dependencies import AuthContext, get_current_context, require_roles
from app.identity.entitlements import check_feature, count_rows
from app.identity.models import Member
from app.identity.schemas import (
    LoginRequest,
    MemberCreate,
    MemberOut,
    MemberUpdate,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TenantOut,
    TenantUpdate,
    TokenResponse,
)

router = APIRouter()


def _token_response(tenant, member, access, refresh) -> TokenResponse:
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=MemberOut.model_validate(member),
        tenant=TenantOut.model_validate(tenant),
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_session)
):
    tenant, member, access, refresh = await service.register_tenant(
        db,
        org_name=payload.org_name,
        slug=payload.slug,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        ip=client_ip(request),
    )
    return _token_response(tenant, member, access, refresh)


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_session)):
    tenant, member, access, refresh = await service.authenticate(
        db,
        email=payload.email,
        password=payload.password,
        tenant_slug=payload.tenant_slug,
        ip=client_ip(request),
    )
    return _token_response(tenant, member, access, refresh)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_session)):
    tenant, member, access, refresh_token = await service.refresh_session(
        db, refresh_token=payload.refresh_token
    )
    return _token_response(tenant, member, access, refresh_token)


@router.get("/me", response_model=MeResponse)
async def me(ctx: AuthContext = Depends(get_current_context)):
    return MeResponse(
        user=MemberOut.model_validate(ctx.member),
        tenant=TenantOut.model_validate(ctx.tenant),
        entitlements={
            "features": ctx.entitlements.features,
            "quotas": ctx.entitlements.quotas,
            "plan_code": ctx.tenant.plan_code,
        },
    )


@router.get("/settings", response_model=TenantOut)
async def get_settings(ctx: AuthContext = Depends(get_current_context)):
    return TenantOut.model_validate(ctx.tenant)


@router.patch("/settings", response_model=TenantOut)
async def update_settings(
    payload: TenantUpdate,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("custom_domain") is not None:
        check_feature(ctx.entitlements, "custom_domain")
    tenant = await service.update_tenant_settings(
        db, actor=ctx.member, tenant=ctx.tenant, updates=updates, ip=client_ip(request)
    )
    return TenantOut.model_validate(tenant)


@router.get("/team/users", response_model=Page[MemberOut])
async def list_team(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    page, page_size, offset = clamp_page(page, page_size)
    members, total = await service.list_members(db, q=q, offset=offset, limit=page_size)
    return Page(
        items=[MemberOut.model_validate(m) for m in members],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/team/users", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_team_member(
    payload: MemberCreate,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    current = await count_rows(db, Member)
    from app.identity.entitlements import check_quota

    check_quota(ctx.entitlements, "max_users", current)

    member, temp_password = await service.create_member(
        db,
        actor=ctx.member,
        tenant_id=ctx.tenant.id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        password=payload.password,
        ip=client_ip(request),
    )
    return {
        "member": MemberOut.model_validate(member),
        "temporary_password": temp_password,
    }


@router.patch("/team/users/{member_id}", response_model=MemberOut)
async def update_team_member(
    member_id: uuid.UUID,
    payload: MemberUpdate,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    member = await service.update_member(
        db,
        actor=ctx.member,
        tenant_id=ctx.tenant.id,
        member_id=member_id,
        full_name=payload.full_name,
        role=payload.role,
        is_active=payload.is_active,
        password=payload.password,
        ip=client_ip(request),
    )
    return MemberOut.model_validate(member)
