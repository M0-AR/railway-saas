"""Schema/application drift detection for the tenant-isolation inventory.

test_rls_enforcement.py proves the flags and the behavioural blindness; this
module proves nobody can add a tenant-scoped table to the schema (or to the
application allow-list) without the other side noticing.
"""

from sqlalchemy import text

from app.db.rls import TENANT_TABLES


async def test_tenant_column_inventory_matches_application_allowlist(owner_engine):
    async with owner_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND column_name = 'tenant_id'
                    """
                )
            )
        ).all()
    derived = {row[0] for row in rows}
    expected = set(TENANT_TABLES)
    assert derived == expected, (
        "TENANT_TABLES drifted from the schema: "
        f"in-schema-only={sorted(derived - expected)}, "
        f"in-app-only={sorted(expected - derived)}"
    )


async def test_each_tenant_table_has_exactly_one_fail_closed_policy(owner_engine):
    async with owner_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    """
                    SELECT tablename, policyname, qual, with_check
                    FROM pg_policies
                    WHERE schemaname = 'public'
                    """
                )
            )
        ).all()

    by_table: dict[str, list[tuple]] = {}
    for row in rows:
        by_table.setdefault(row[0], []).append(row)

    for table in TENANT_TABLES:
        policies = by_table.get(table, [])
        names = [policy[1] for policy in policies]
        assert names == [f"{table}_tenant_isolation"], f"{table}: unexpected policies {names}"

        _, _, qual, with_check = policies[0]
        for expression in (qual, with_check):
            assert expression, f"{table}: policy expression missing"
            assert "current_setting" in expression, f"{table}: not context-dependent"
            assert "NULLIF" in expression, f"{table}: not fail-closed on empty context"
