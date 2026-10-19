"""Database-level proof of the isolation claim:

- every tenant table has RLS enabled AND forced;
- every policy is written fail-closed around app.current_tenant;
- the runtime role (railway_app) neither is superuser nor bypasses RLS.
"""

from sqlalchemy import text

from tests.conftest import APP_DB_URL as APP_DB
from tests.conftest import register_tenant

TENANT_TABLES = [
    "member",
    "train",
    "train_inventory",
    "booking",
    "booking_passenger",
    "audit_log",
]


async def test_rls_enabled_and_forced_on_every_tenant_table(owner_engine):
    async with owner_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    """
                    SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relkind = 'r'
                    """
                )
            )
        ).all()
    flags = {row[0]: (row[1], row[2]) for row in rows}

    for table in TENANT_TABLES:
        assert table in flags, f"{table} missing from schema"
        rls_enabled, rls_forced = flags[table]
        assert rls_enabled, f"{table}: RLS not enabled"
        assert rls_forced, f"{table}: RLS not FORCED"

    assert flags.get("tenant", (True, True))[1] is False, "global tenant table should have RLS off"
    assert flags.get("plan", (True, True))[1] is False, "global plan table should have RLS off"


async def test_policies_are_fail_closed(owner_engine):
    async with owner_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    """
                    SELECT tablename, qual
                    FROM pg_policies
                    WHERE schemaname = 'public'
                    """
                )
            )
        ).all()

    policies: dict[str, list[str]] = {}
    for tablename, qual in rows:
        policies.setdefault(tablename, []).append(qual or "")

    for table in TENANT_TABLES:
        assert policies.get(table), f"{table}: no RLS policy"
        assert any("current_setting" in qual for qual in policies[table]), (
            f"{table}: policy does not depend on app.current_tenant"
        )
        assert any("NULLIF" in qual for qual in policies[table]), (
            f"{table}: policy does not fail closed on empty tenant setting"
        )


async def test_runtime_role_cannot_bypass_rls(owner_engine, client):
    registered = await register_tenant(client)

    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(APP_DB)
    try:
        async with engine.connect() as conn:
            role = (
                await conn.execute(
                    text(
                        """
                        SELECT current_user, rolsuper, rolbypassrls
                        FROM pg_roles WHERE rolname = current_user
                        """
                    )
                )
            ).one()
            assert role[0] == "railway_app"
            assert role[1] is False, "runtime role must not be superuser"
            assert role[2] is False, "runtime role must not have BYPASSRLS"

        # Even though registration wrote rows, a context-less connection sees none.
        async with engine.begin() as conn:
            for table in ("member", "tenant"):
                count = await conn.scalar(text(f"SELECT count(*) FROM {table}"))  # noqa: S608
                if table == "tenant":
                    assert count == 1  # global table: visible
                else:
                    assert count == 0  # tenant-scoped: fail-closed
    finally:
        await engine.dispose()

    assert registered
