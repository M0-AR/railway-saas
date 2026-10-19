"""Row-Level Security helpers.

Verified operating rules (OWASP multi-tenant cheat sheet, PlanetScale, aws blog):
- request path connects as a role that owns nothing and cannot bypass RLS;
- tenant id is set per transaction (set_config(..., is_local=true));
- policies fail closed via NULLIF(current_setting('app.current_tenant', true), '');
- startup must refuse to run if any tenant table is not FORCE-RLS protected.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TENANT_TABLES: tuple[str, ...] = (
    "member",
    "train",
    "train_inventory",
    "booking",
    "booking_passenger",
    "audit_log",
)


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID | str | None) -> None:
    tenant = str(tenant_id) if tenant_id else ""
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tenant, true)"), {"tenant": tenant}
    )


async def verify_rls_enforcement(session: AsyncSession) -> list[str]:
    """Returns a list of problems. Empty list means enforcement is intact."""
    problems: list[str] = []

    row = (
        await session.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        )
    ).first()
    if row is None:
        problems.append("could not read current role from pg_roles")
    elif row[0] or row[1]:
        problems.append(
            f"request role bypasses RLS (rolsuper={row[0]}, rolbypassrls={row[1]}); "
            "the app must connect as a NOSUPERUSER NOBYPASSRLS role"
        )

    protected = {
        r[0]
        for r in (
            await session.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r' "
                    "AND c.relrowsecurity AND c.relforcerowsecurity"
                )
            )
        ).all()
    }
    missing = [t for t in TENANT_TABLES if t not in protected]
    if missing:
        problems.append(f"tenant tables missing FORCE RLS: {', '.join(missing)}")

    return problems
