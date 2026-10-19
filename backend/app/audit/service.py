import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    actor_email: str,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    payload: dict[str, Any] | None = None,
    ip: str = "",
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
            ip=ip,
        )
    )
