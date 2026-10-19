import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog
from app.core.pagination import Page, clamp_page
from app.db.session import get_session
from app.identity.dependencies import AuthContext, require_feature, require_roles

router = APIRouter()


class AuditOut(BaseModel):
    id: uuid.UUID
    actor_email: str
    action: str
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    ip: str
    created_at: datetime


@router.get("", response_model=Page[AuditOut])
async def list_audit_log(
    action: str | None = None,
    entity_type: str | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    _feature: AuthContext = Depends(require_feature("audit.view")),
    db: AsyncSession = Depends(get_session),
):
    conditions = [AuditLog.tenant_id == ctx.tenant.id]
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if q:
        pattern = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(AuditLog.actor_email).like(pattern),
                func.lower(AuditLog.action).like(pattern),
                func.lower(AuditLog.entity_id).like(pattern),
            )
        )
    if date_from:
        conditions.append(func.date(AuditLog.created_at) >= date_from)
    if date_to:
        conditions.append(func.date(AuditLog.created_at) <= date_to)

    page, page_size, offset = clamp_page(page, page_size)

    stmt = (
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    count_stmt = select(func.count()).select_from(AuditLog).where(*conditions)
    entries = list((await db.execute(stmt)).scalars().all())
    total = int((await db.execute(count_stmt)).scalar_one())

    return Page(
        items=[AuditOut.model_validate(entry, from_attributes=True) for entry in entries],
        total=total,
        page=page,
        page_size=page_size,
    )
