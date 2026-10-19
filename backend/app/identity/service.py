import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import jwt
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.core.errors import AuthError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db.rls import set_tenant_context
from app.identity.models import Member, Plan, Tenant
from app.identity.plans import DEFAULT_PLAN_CODE, PLAN_DEFINITIONS

DEFAULT_BRANDING: dict[str, Any] = {
    "primary_color": "#6d5efc",
    "accent_color": "#22d3ee",
    "support_email": "",
}


async def ensure_plans(db: AsyncSession) -> None:
    for definition in PLAN_DEFINITIONS:
        existing = await db.get(Plan, definition["code"])
        values = {k: v for k, v in definition.items() if k != "code"}
        if existing is None:
            db.add(Plan(code=definition["code"], **values))
        else:
            for key, value in values.items():
                setattr(existing, key, value)
    await db.flush()


async def get_plan(db: AsyncSession, code: str) -> Plan | None:
    return await db.get(Plan, code)


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    return await db.get(Tenant, tenant_id)


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug.lower()))
    return result.scalar_one_or_none()


async def get_tenant_by_domain(db: AsyncSession, domain: str) -> Tenant | None:
    domain = domain.lower().split(":")[0]
    result = await db.execute(select(Tenant).where(Tenant.custom_domain == domain))
    return result.scalar_one_or_none()


def _issue_tokens(member: Member) -> tuple[str, str]:
    access = create_token(
        user_id=member.id, tenant_id=member.tenant_id, role=member.role, token_type="access"
    )
    refresh = create_token(
        user_id=member.id, tenant_id=member.tenant_id, role=member.role, token_type="refresh"
    )
    return access, refresh


async def register_tenant(
    db: AsyncSession,
    *,
    org_name: str,
    slug: str,
    full_name: str,
    email: str,
    password: str,
    ip: str = "",
) -> tuple[Tenant, Member, str, str]:
    await ensure_plans(db)

    if await get_tenant_by_slug(db, slug):
        raise ConflictError("This workspace URL is already taken.")

    tenant = Tenant(
        slug=slug,
        name=org_name,
        plan_code=DEFAULT_PLAN_CODE,
        branding={**DEFAULT_BRANDING, "logo_text": org_name},
    )
    try:
        async with db.begin_nested():
            db.add(tenant)
    except IntegrityError as exc:
        raise ConflictError("This workspace URL is already taken.") from exc

    await set_tenant_context(db, tenant.id)

    member = Member(
        tenant_id=tenant.id,
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        role="owner",
    )
    try:
        async with db.begin_nested():
            db.add(member)
    except IntegrityError as exc:
        raise ConflictError("An account with this email already exists.") from exc

    await record_audit(
        db,
        tenant_id=tenant.id,
        actor_id=member.id,
        actor_email=member.email,
        action="tenant.provisioned",
        entity_type="tenant",
        entity_id=str(tenant.id),
        payload={"slug": slug, "org_name": org_name},
        ip=ip,
    )
    access, refresh = _issue_tokens(member)
    return tenant, member, access, refresh


async def authenticate(
    db: AsyncSession, *, email: str, password: str, tenant_slug: str | None, ip: str = ""
) -> tuple[Tenant, Member, str, str]:
    if not tenant_slug:
        raise AuthError("Workspace is required. Open your workspace URL to sign in.")
    tenant = await get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise AuthError("Invalid email or password.")
    if tenant.status != "active":
        raise ForbiddenError("This workspace is currently suspended.")

    await set_tenant_context(db, tenant.id)
    result = await db.execute(
        select(Member).where(Member.email == email.lower(), Member.tenant_id == tenant.id)
    )
    member = result.scalar_one_or_none()
    if member is None or not verify_password(password, member.password_hash):
        raise AuthError("Invalid email or password.")
    if not member.is_active:
        raise ForbiddenError("Your account has been deactivated. Contact your administrator.")

    member.last_login_at = datetime.now(UTC)
    await record_audit(
        db,
        tenant_id=tenant.id,
        actor_id=member.id,
        actor_email=member.email,
        action="auth.login",
        entity_type="member",
        entity_id=str(member.id),
        ip=ip,
    )
    access, refresh = _issue_tokens(member)
    return tenant, member, access, refresh


async def refresh_session(
    db: AsyncSession, *, refresh_token: str
) -> tuple[Tenant, Member, str, str]:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise AuthError("Session expired. Please sign in again.") from exc

    tenant = await get_tenant(db, uuid.UUID(payload["tid"]))
    if tenant is None or tenant.status != "active":
        raise AuthError("Session expired. Please sign in again.")
    await set_tenant_context(db, tenant.id)
    member = await db.get(Member, uuid.UUID(payload["sub"]))
    if member is None or not member.is_active:
        raise AuthError("Session expired. Please sign in again.")
    access, refresh = _issue_tokens(member)
    return tenant, member, access, refresh


async def list_members(
    db: AsyncSession, *, q: str | None, offset: int, limit: int
) -> tuple[list[Member], int]:
    stmt = select(Member)
    count_stmt = select(func.count()).select_from(Member)
    if q:
        pattern = f"%{q.strip().lower()}%"
        condition = or_(
            func.lower(Member.email).like(pattern), func.lower(Member.full_name).like(pattern)
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    stmt = stmt.order_by(Member.created_at.asc()).offset(offset).limit(limit)
    members = list((await db.execute(stmt)).scalars().all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return members, total


MANAGER_ROLES = ("owner", "admin")


def _assert_can_manage(actor: Member, target_role: str | None = None) -> None:
    if actor.role not in MANAGER_ROLES:
        raise ForbiddenError("You do not have permission to manage team members.")
    if target_role in ("owner", "admin") and actor.role != "owner":
        raise ForbiddenError("Only the workspace owner can manage admins.")


async def create_member(
    db: AsyncSession,
    *,
    actor: Member,
    tenant_id: uuid.UUID,
    email: str,
    full_name: str,
    role: str,
    password: str | None,
    ip: str = "",
) -> tuple[Member, str | None]:
    _assert_can_manage(actor, role)
    temp_password: str | None = None
    if password is None:
        temp_password = secrets.token_urlsafe(9)
        password = temp_password

    member = Member(
        tenant_id=tenant_id,
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
    )
    try:
        async with db.begin_nested():
            db.add(member)
    except IntegrityError as exc:
        raise ConflictError("A team member with this email already exists.") from exc

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="team.member_created",
        entity_type="member",
        entity_id=str(member.id),
        payload={"email": email, "role": role},
        ip=ip,
    )
    return member, temp_password


async def update_member(
    db: AsyncSession,
    *,
    actor: Member,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    full_name: str | None,
    role: str | None,
    is_active: bool | None,
    password: str | None,
    ip: str = "",
) -> Member:
    _assert_can_manage(actor, role)

    target = await db.get(Member, member_id)
    if target is None:
        raise NotFoundError("Team member not found.")
    if target.id == actor.id and (role is not None and role != actor.role):
        raise ForbiddenError("You cannot change your own role.")
    if target.id == actor.id and is_active is False:
        raise ForbiddenError("You cannot deactivate your own account.")
    if target.role == "owner" and actor.role != "owner":
        raise ForbiddenError("Only the workspace owner can modify the owner account.")
    if role == "owner":
        raise ForbiddenError("Ownership transfer is not supported yet.")

    if target.role == "owner" and (role not in (None, "owner") or is_active is False):
        owner_count = int(
            (
                await db.execute(
                    select(func.count()).select_from(Member).where(Member.role == "owner")
                )
            ).scalar_one()
        )
        if owner_count <= 1:
            raise ConflictError("The workspace must keep at least one owner.")

    if full_name is not None:
        target.full_name = full_name
    if role is not None:
        target.role = role
    if is_active is not None:
        target.is_active = is_active
    if password is not None:
        target.password_hash = hash_password(password)

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="team.member_updated",
        entity_type="member",
        entity_id=str(target.id),
        payload={"full_name": full_name, "role": role, "is_active": is_active,
                 "password_reset": password is not None},
        ip=ip,
    )
    return target


async def update_tenant_settings(
    db: AsyncSession,
    *,
    actor: Member,
    tenant: Tenant,
    updates: dict[str, Any],
    ip: str = "",
) -> Tenant:
    if "name" in updates and updates["name"] is not None:
        tenant.name = updates["name"]
    if "branding" in updates and updates["branding"] is not None:
        tenant.branding = {**(tenant.branding or {}), **updates["branding"]}
    if "default_currency" in updates and updates["default_currency"] is not None:
        tenant.default_currency = updates["default_currency"].upper()
    if "locale" in updates and updates["locale"] is not None:
        tenant.locale = updates["locale"]
    if "timezone" in updates and updates["timezone"] is not None:
        tenant.timezone = updates["timezone"]
    if "custom_domain" in updates and updates["custom_domain"] is not None:
        domain = updates["custom_domain"].strip().lower() or None
        if domain == "":
            domain = None
        if domain is not None and domain != tenant.custom_domain:
            clash = await get_tenant_by_domain(db, domain)
            if clash is not None and clash.id != tenant.id:
                raise ConflictError("This domain is already connected to another workspace.")
        tenant.custom_domain = domain

    await record_audit(
        db,
        tenant_id=tenant.id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="settings.updated",
        entity_type="tenant",
        entity_id=str(tenant.id),
        payload={k: v for k, v in updates.items() if v is not None},
        ip=ip,
    )
    return tenant
