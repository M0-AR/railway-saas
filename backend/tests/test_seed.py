"""Seed: idempotent, tiered, deterministic demo data that reports can trust."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bookings.models import Booking, BookingPassenger
from app.db.rls import set_tenant_context
from app.identity.models import Member, Tenant
from app.seed import DEMO_PASSWORD, TENANT_SPECS, seed_all
from app.trains.models import Train
from tests.conftest import API, auth, login


@pytest.fixture
async def seeded(owner_engine):
    factory = async_sessionmaker(owner_engine, expire_on_commit=False)
    async with factory() as session:
        created = await seed_all(session)
        await session.commit()
    return {"factory": factory, "created": created}


async def _tenant_id(session, slug: str):
    return (
        await session.execute(select(Tenant.id).where(Tenant.slug == slug))
    ).scalar_one()


async def _tenant_rows(session, tenant_id):
    await set_tenant_context(session, tenant_id)
    members = list((await session.execute(select(Member))).scalars())
    trains = list((await session.execute(select(Train))).scalars())
    bookings = list((await session.execute(select(Booking))).scalars())
    passengers = list((await session.execute(select(BookingPassenger))).scalars())
    return members, trains, bookings, passengers


async def test_seed_is_complete_and_idempotent(seeded):
    assert seeded["created"] == {spec.slug: True for spec in TENANT_SPECS}

    factory = seeded["factory"]
    async with factory() as session:
        again = await seed_all(session)
        await session.commit()
    assert again == {spec.slug: False for spec in TENANT_SPECS}

    async with factory() as session:
        for spec in TENANT_SPECS:
            members, trains, bookings, _ = await _tenant_rows(
                session, await _tenant_id(session, spec.slug)
            )
            assert len(members) == len(spec.members), spec.slug
            assert len(trains) == len(spec.trains), spec.slug
            expected = spec.forward_bookings + spec.history_bookings
            assert len(bookings) == expected, spec.slug


async def test_ledger_is_realistic_and_pii_safe(seeded):
    factory = seeded["factory"]
    now = datetime.now(UTC)
    today = date.today()

    async with factory() as session:
        for spec in TENANT_SPECS:
            members, trains, bookings, passengers = await _tenant_rows(
                session, await _tenant_id(session, spec.slug)
            )

            assert sum(1 for member in members if member.role == "owner") == 1
            assert {member.email for member in members} == {
                email for email, _, _ in spec.members
            }

            train_ids = {train.id for train in trains}
            assert {booking.train_id for booking in bookings} <= train_ids
            assert all(booking.currency == "USD" for booking in bookings)
            assert len({booking.pnr for booking in bookings}) == len(bookings)
            assert all(booking.created_at <= now for booking in bookings)
            assert min(booking.created_at for booking in bookings) <= now - timedelta(days=30)

            cancelled = [booking for booking in bookings if booking.status == "cancelled"]
            assert cancelled, spec.slug
            assert all(
                booking.refund_status in {"pending", "processed"} for booking in cancelled
            )
            assert all(
                booking.refund_status == "none"
                for booking in bookings
                if booking.status == "confirmed"
            )
            assert len(passengers) == sum(booking.seats for booking in bookings)

            assert all(member.email.endswith(".demo") for member in members)
            assert all(booking.contact_email.endswith("example.com") for booking in bookings)
            assert all(booking.contact_phone.startswith("+1-555-") for booking in bookings)

            recent_cutoff = now - timedelta(minutes=10)
            forward = [booking for booking in bookings if booking.created_at >= recent_cutoff]
            assert len(forward) == spec.forward_bookings, spec.slug
            assert all(booking.travel_date >= today for booking in forward)
            assert (
                sum(1 for booking in forward if booking.status == "cancelled")
                == len(range(0, len(forward), 4))
            )


async def test_seeded_tenants_are_isolated(seeded):
    factory = seeded["factory"]
    async with factory() as session:
        per_tenant: dict[str, dict[str, set]] = {}
        for spec in TENANT_SPECS:
            _, trains, bookings, _ = await _tenant_rows(
                session, await _tenant_id(session, spec.slug)
            )
            per_tenant[spec.slug] = {
                "trains": {train.id for train in trains},
                "bookings": {booking.train_id for booking in bookings},
            }

    all_train_ids = [
        train_id for data in per_tenant.values() for train_id in data["trains"]
    ]
    assert len(all_train_ids) == len(set(all_train_ids))
    for data in per_tenant.values():
        assert data["bookings"] <= data["trains"]


async def test_seeded_workspace_is_usable_end_to_end(client, seeded):
    demo = await login(
        client, slug="demo", email="demo@railway.demo", password=DEMO_PASSWORD
    )
    headers = auth(demo["access_token"])

    me = await client.get(f"{API}/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["tenant"]["slug"] == "demo"
    assert body["user"]["role"] == "owner"
    assert body["entitlements"]["plan_code"] == "growth"

    trains = await client.get(f"{API}/trains", params={"page_size": 100}, headers=headers)
    assert trains.json()["total"] == 12

    bookings = await client.get(f"{API}/bookings", params={"page_size": 100}, headers=headers)
    assert bookings.json()["total"] == 48

    overview = (await client.get(f"{API}/reports/overview", headers=headers)).json()
    assert overview["trains"] == {"active": 12, "total": 12}
    assert overview["bookings"]["today"] == 16
    assert overview["revenue"]["today_cents"] > 0
    assert overview["cancellation_rate_30d"] > 0

    starter = await login(
        client, slug="starter", email="owner@starter.demo", password=DEMO_PASSWORD
    )
    starter_headers = auth(starter["access_token"])
    assert (
        await client.get(f"{API}/reports/overview", headers=starter_headers)
    ).status_code == 200
    gated = await client.get(f"{API}/reports/revenue", headers=starter_headers)
    assert gated.status_code == 402
    assert gated.json()["error"]["code"] == "entitlement_required"
