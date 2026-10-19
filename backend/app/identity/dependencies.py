import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_token
from app.db.rls import set_tenant_context
from app.db.session import get_session
from app.identity.entitlements import Entitlements, check_feature, resolve_entitlements
from app.identity.models import Member, Plan, Tenant
from app.identity.service import get_plan, get_tenant

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    member: Member
    tenant: Tenant
    plan: Plan | None
    entitlements: Entitlements


async def get_current_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> AuthContext:
    if credentials is None:
        raise AuthError("Not authenticated.")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        tenant_id = uuid.UUID(payload["tid"])
        member_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthError("Invalid or expired token.") from exc

    tenant = await get_tenant(db, tenant_id)
    if tenant is None:
        raise AuthError("Invalid or expired token.")
    if tenant.status != "active":
        raise ForbiddenError("This workspace is currently suspended.")

    plan = await get_plan(db, tenant.plan_code)

    # All tenant-scoped queries below only see rows of this tenant.
    await set_tenant_context(db, tenant.id)
    member = await db.get(Member, member_id)
    if member is None or member.tenant_id != tenant.id:
        raise AuthError("Invalid or expired token.")
    if not member.is_active:
        raise ForbiddenError("Your account has been deactivated.")

    entitlements = resolve_entitlements(
        plan.features if plan else {},
        plan.quotas if plan else {},
        tenant.features_override,
    )
    return AuthContext(member=member, tenant=tenant, plan=plan, entitlements=entitlements)


def require_roles(*roles: str):
    async def dependency(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        if ctx.member.role not in roles:
            raise ForbiddenError("Your role does not allow this action.")
        return ctx

    return dependency


def require_feature(key: str):
    async def dependency(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        check_feature(ctx.entitlements, key)
        return ctx

    return dependency
