"""Cross-tenant isolation — the product's core security claim.

Layer 1: API — tenant B can never see or touch tenant A's rows by id.
Layer 2: Database — the runtime role, with no or wrong tenant context, sees
nothing even when rows exist (FORCE RLS fail-closed).
"""

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import API, auth, create_train, register_tenant
from tests.conftest import APP_DB_URL as APP_DB


async def _two_tenants(client):
    a = await register_tenant(
        client, slug="alpha", email="owner@alpha.example", org_name="Alpha Rail"
    )
    b = await register_tenant(
        client, slug="beta", email="owner@beta.example", org_name="Beta Rail"
    )
    return a, b


async def test_api_never_leaks_across_tenants(client):
    a, b = await _two_tenants(client)
    token_a, token_b = a["access_token"], b["access_token"]

    train = await create_train(client, token_a, number="AL-1", name="Alpha Express")
    travel = (date.today() + timedelta(days=1)).isoformat()
    booked = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": travel,
            "seats": 1,
            "contact_name": "Alpha Passenger",
        },
        headers=auth(token_a),
    )
    assert booked.status_code == 201, booked.text
    booking_id = booked.json()["id"]

    assert (await client.get(f"{API}/trains", headers=auth(token_b))).json()["total"] == 0
    assert (
        await client.get(f"{API}/trains/{train['id']}", headers=auth(token_b))
    ).status_code == 404
    assert (
        await client.patch(
            f"{API}/trains/{train['id']}", json={"name": "Hijacked"}, headers=auth(token_b)
        )
    ).status_code == 404
    assert (
        await client.delete(f"{API}/trains/{train['id']}", headers=auth(token_b))
    ).status_code == 404

    assert (await client.get(f"{API}/bookings", headers=auth(token_b))).json()["total"] == 0
    assert (
        await client.get(f"{API}/bookings/{booking_id}", headers=auth(token_b))
    ).status_code == 404
    assert (
        await client.post(f"{API}/bookings/{booking_id}/cancel", headers=auth(token_b))
    ).status_code == 404

    assert (await client.get(f"{API}/trains", headers=auth(token_a))).json()["total"] == 1
    assert (
        await client.get(f"{API}/bookings/{booking_id}", headers=auth(token_a))
    ).status_code == 200


async def test_database_role_is_blind_without_tenant_context(client):
    a, b = await _two_tenants(client)
    await create_train(client, a["access_token"], number="AL-2", name="Alpha Night")

    engine = create_async_engine(APP_DB)
    try:
        # No context set anywhere: fail closed, zero rows even though data exists.
        async with engine.begin() as conn:
            assert await conn.scalar(text("SELECT count(*) FROM train")) == 0
            assert await conn.scalar(text("SELECT count(*) FROM member")) == 0
            assert await conn.scalar(text("SELECT count(*) FROM audit_log")) == 0

        # Wrong tenant's context: still zero rows.
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.current_tenant', :tid, true)"),
                {"tid": b["tenant"]["id"]},
            )
            assert await conn.scalar(text("SELECT count(*) FROM train")) == 0

        # Right tenant's context (transaction-local, like production): visible.
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.current_tenant', :tid, true)"),
                {"tid": a["tenant"]["id"]},
            )
            assert await conn.scalar(text("SELECT count(*) FROM train")) == 1

        # The local setting died with its transaction: blind again.
        async with engine.begin() as conn:
            assert await conn.scalar(text("SELECT count(*) FROM train")) == 0
    finally:
        await engine.dispose()


async def test_login_is_scoped_to_the_stated_tenant(client):
    a, _ = await _two_tenants(client)

    mismatched = await client.post(
        f"{API}/auth/login",
        json={"email": "owner@alpha.example", "password": "Passw0rd!234", "tenant_slug": "beta"},
    )
    assert mismatched.status_code == 401

    correct = await client.post(
        f"{API}/auth/login",
        json={"email": "owner@alpha.example", "password": "Passw0rd!234", "tenant_slug": "alpha"},
    )
    assert correct.status_code == 200
    assert correct.json()["tenant"]["id"] == a["tenant"]["id"]
