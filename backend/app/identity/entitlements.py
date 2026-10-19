from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import EntitlementError, QuotaExceededError

UNLIMITED = -1


@dataclass(frozen=True)
class Entitlements:
    features: dict[str, bool]
    quotas: dict[str, int]

    def has(self, key: str) -> bool:
        return bool(self.features.get(key, False))

    def quota(self, key: str) -> int:
        return int(self.quotas.get(key, 0))


def resolve_entitlements(
    plan_features: dict[str, Any] | None,
    plan_quotas: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> Entitlements:
    overrides = overrides or {}
    features = {**(plan_features or {}), **(overrides.get("features") or {})}
    quotas = {**(plan_quotas or {}), **(overrides.get("quotas") or {})}
    return Entitlements(features=features, quotas=quotas)


def check_feature(entitlements: Entitlements, key: str) -> None:
    if not entitlements.has(key):
        raise EntitlementError(
            f"This feature ({key}) is not included in your current plan.",
            details={"feature": key, "upgrade_required": True},
        )


def check_quota(entitlements: Entitlements, key: str, current: int) -> None:
    quota = entitlements.quota(key)
    if quota == UNLIMITED:
        return
    if current >= quota:
        raise QuotaExceededError(
            f"Plan limit reached for {key} ({quota}). Upgrade your plan to add more.",
            details={"quota": key, "limit": quota, "current": current},
        )


async def count_rows(db: AsyncSession, model: Any, *filters: Any) -> int:
    stmt = select(func.count()).select_from(model).where(*filters)
    return int((await db.execute(stmt)).scalar_one())
