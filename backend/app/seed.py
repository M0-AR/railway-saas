"""Deterministic multi-tenant demo seed.

Three workspaces demonstrate the product at different plan tiers:

- ``demo``      (growth)     4 staff, 12 trains, forward + 60 days of history
- ``northline`` (enterprise) 5 staff, 6 trains, the busiest booking ledger
- ``starter``   (starter)    2 staff, 2 trains, useful for plan-gate screenshots

Forward bookings go through the real booking service, so seat inventory and
audit rows stay consistent; a deterministic slice is then cancelled. Historical
bookings are inserted directly with backdated timestamps for reports.

All content is synthetic (``*.demo`` staff, ``example.com`` contacts,
``+1-555-01xx`` phones) and every RNG is seeded per tenant, so a fresh database
seeded on the same day yields identical counts, amounts and statuses. PNRs are
random by design and therefore the only non-deterministic field.

Idempotent: a workspace is only created when its slug is absent.

Run: python -m app.seed   (or set SEED_DEMO=true to run at API startup)
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.bookings.models import Booking, BookingPassenger
from app.bookings.schemas import BookingCreate, PassengerIn
from app.bookings.service import _generate_pnr, cancel_booking, create_booking
from app.core.security import hash_password
from app.db.rls import set_tenant_context
from app.db.session import async_session_maker
from app.identity.entitlements import resolve_entitlements
from app.identity.models import Member, Tenant
from app.identity.service import ensure_plans, get_plan, get_tenant_by_slug
from app.trains.models import Train

DEMO_SLUG = "demo"
DEMO_PASSWORD = "demo1234"
CHANNELS = ("counter", "online", "phone", "agent")
ALL_DAYS = [1, 2, 3, 4, 5, 6, 7]

DEMO_MEMBERS = [
    ("demo@railway.demo", "Dana Okafor", "owner"),
    ("manager@railway.demo", "Miguel Santos", "manager"),
    ("agent@railway.demo", "Aisha Rahman", "agent"),
    ("viewer@railway.demo", "Viktor Petrov", "viewer"),
]

NORTHLINE_MEMBERS = [
    ("owner@northline.demo", "Ingrid Solberg", "owner"),
    ("ops@northline.demo", "Marcus Chen", "manager"),
    ("revenue@northline.demo", "Fatima Al-Sayed", "manager"),
    ("agent@northline.demo", "Tomasz Nowak", "agent"),
    ("viewer@northline.demo", "Chiara Bianchi", "viewer"),
]

STARTER_MEMBERS = [
    ("owner@starter.demo", "Ruth Mensah", "owner"),
    ("agent@starter.demo", "Diego Alvarez", "agent"),
]

DEMO_TRAINS = [
    {
        "number": "AE-101",
        "name": "Aurora Express",
        "train_type": "express",
        "source": "Meridian Central",
        "destination": "Northgate",
        "departure_time": time(7, 15),
        "arrival_time": time(12, 40),
        "total_seats": 220,
        "fare_cents": 3450,
        "stops": [
            {"name": "Brookfield", "offset_minutes": 85},
            {"name": "Havenport", "offset_minutes": 190},
        ],
    },
    {
        "number": "CS-204",
        "name": "Coastal Sprinter",
        "train_type": "intercity",
        "source": "Bayport",
        "destination": "Cliffside",
        "departure_time": time(8, 0),
        "arrival_time": time(10, 20),
        "total_seats": 140,
        "fare_cents": 1800,
        "stops": [{"name": "Seabrook", "offset_minutes": 70}],
    },
    {
        "number": "HF-330",
        "name": "Highland Flyer",
        "train_type": "express",
        "source": "Highland Junction",
        "destination": "Meridian Central",
        "departure_time": time(9, 30),
        "arrival_time": time(15, 10),
        "total_seats": 260,
        "fare_cents": 4125,
        "stops": [
            {"name": "Glenmore", "offset_minutes": 120},
            {"name": "Brookfield", "offset_minutes": 260},
        ],
    },
    {
        "number": "NH-500",
        "name": "Night Horizon",
        "train_type": "sleeper",
        "source": "Northgate",
        "destination": "Bayport",
        "departure_time": time(22, 10),
        "arrival_time": time(6, 45),
        "total_seats": 180,
        "fare_cents": 5800,
        "stops": [{"name": "Havenport", "offset_minutes": 240}],
    },
    {
        "number": "VL-612",
        "name": "Valley Local",
        "train_type": "regional",
        "source": "Cliffside",
        "destination": "Valley Forge",
        "departure_time": time(6, 40),
        "arrival_time": time(9, 5),
        "total_seats": 120,
        "fare_cents": 975,
        "stops": [],
    },
    {
        "number": "ML-720",
        "name": "Metro Lark",
        "train_type": "commuter",
        "source": "Northgate",
        "destination": "Bayport",
        "departure_time": time(17, 30),
        "arrival_time": time(18, 5),
        "total_seats": 300,
        "fare_cents": 650,
        "stops": [],
    },
    {
        "number": "CT-900",
        "name": "Continental",
        "train_type": "high_speed",
        "source": "Meridian Central",
        "destination": "Bayport",
        "departure_time": time(12, 0),
        "arrival_time": time(15, 30),
        "total_seats": 320,
        "fare_cents": 5200,
        "stops": [{"name": "Brookfield", "offset_minutes": 95}],
    },
    {
        "number": "SR-450",
        "name": "Sunrise Regional",
        "train_type": "regional",
        "source": "Valley Forge",
        "destination": "Northgate",
        "departure_time": time(5, 55),
        "arrival_time": time(11, 20),
        "total_seats": 160,
        "fare_cents": 1235,
        "stops": [{"name": "Havenport", "offset_minutes": 150}],
    },
    {
        "number": "CG-880",
        "name": "Cascade Grand",
        "train_type": "high_speed",
        "source": "Meridian Central",
        "destination": "Northgate",
        "departure_time": time(14, 45),
        "arrival_time": time(18, 10),
        "total_seats": 280,
        "fare_cents": 4900,
        "stops": [{"name": "Glenmore", "offset_minutes": 110}],
    },
    {
        "number": "LL-240",
        "name": "Lakeside Loop",
        "train_type": "regional",
        "source": "Bayport",
        "destination": "Valley Forge",
        "departure_time": time(10, 25),
        "arrival_time": time(13, 5),
        "total_seats": 130,
        "fare_cents": 1050,
        "stops": [{"name": "Seabrook", "offset_minutes": 55}],
    },
    {
        "number": "SC-570",
        "name": "Southern Cross",
        "train_type": "intercity",
        "source": "Northgate",
        "destination": "Cliffside",
        "departure_time": time(13, 20),
        "arrival_time": time(17, 55),
        "total_seats": 190,
        "fare_cents": 2200,
        "stops": [{"name": "Brookfield", "offset_minutes": 145}],
    },
    {
        "number": "WT-610",
        "name": "Winterlude",
        "train_type": "sleeper",
        "source": "Bayport",
        "destination": "Meridian Central",
        "departure_time": time(21, 40),
        "arrival_time": time(6, 10),
        "total_seats": 170,
        "fare_cents": 6100,
        "stops": [{"name": "Havenport", "offset_minutes": 200}],
    },
]

NORTHLINE_TRAINS = [
    {
        "number": "NR-001",
        "name": "Northern Star",
        "train_type": "high_speed",
        "source": "Meridian Central",
        "destination": "Northgate",
        "departure_time": time(6, 55),
        "arrival_time": time(10, 15),
        "total_seats": 320,
        "fare_cents": 4800,
        "stops": [{"name": "Brookfield", "offset_minutes": 80}],
    },
    {
        "number": "NR-014",
        "name": "Arctic Light",
        "train_type": "sleeper",
        "source": "Northgate",
        "destination": "Bayport",
        "departure_time": time(23, 5),
        "arrival_time": time(7, 30),
        "total_seats": 200,
        "fare_cents": 6400,
        "stops": [{"name": "Havenport", "offset_minutes": 250}],
    },
    {
        "number": "NR-022",
        "name": "Fjord Runner",
        "train_type": "express",
        "source": "Bayport",
        "destination": "Cliffside",
        "departure_time": time(9, 10),
        "arrival_time": time(13, 35),
        "total_seats": 180,
        "fare_cents": 2900,
        "stops": [{"name": "Seabrook", "offset_minutes": 95}],
    },
    {
        "number": "NR-108",
        "name": "Boreal Local",
        "train_type": "regional",
        "source": "Cliffside",
        "destination": "Valley Forge",
        "departure_time": time(7, 40),
        "arrival_time": time(10, 30),
        "total_seats": 140,
        "fare_cents": 1100,
        "stops": [],
    },
    {
        "number": "NR-210",
        "name": "Tundra Commuter",
        "train_type": "commuter",
        "source": "Northgate",
        "destination": "Bayport",
        "departure_time": time(17, 55),
        "arrival_time": time(18, 40),
        "total_seats": 260,
        "fare_cents": 700,
        "stops": [],
    },
    {
        "number": "NR-333",
        "name": "Glacier Line",
        "train_type": "intercity",
        "source": "Meridian Central",
        "destination": "Cliffside",
        "departure_time": time(11, 30),
        "arrival_time": time(16, 5),
        "total_seats": 220,
        "fare_cents": 3600,
        "stops": [{"name": "Brookfield", "offset_minutes": 120}],
    },
]

STARTER_TRAINS = [
    {
        "number": "SJ-01",
        "name": "Junction Shuttle",
        "train_type": "regional",
        "source": "Valley Forge",
        "destination": "Meridian Central",
        "departure_time": time(8, 15),
        "arrival_time": time(10, 45),
        "total_seats": 90,
        "fare_cents": 850,
        "stops": [],
    },
    {
        "number": "SJ-02",
        "name": "Morning Local",
        "train_type": "commuter",
        "source": "Meridian Central",
        "destination": "Bayport",
        "departure_time": time(7, 5),
        "arrival_time": time(8, 20),
        "total_seats": 120,
        "fare_cents": 600,
        "stops": [],
    },
]

CONTACTS = [
    ("Grace Lindqvist", "grace.l@example.com", "+1-555-0101"),
    ("Tomás Herrera", "tomas.h@example.com", "+1-555-0102"),
    ("Priya Nair", "priya.n@example.com", "+1-555-0103"),
    ("Jonas Weber", "jonas.w@example.com", "+1-555-0104"),
    ("Amara Diallo", "amara.d@example.com", "+1-555-0105"),
    ("Kenji Watanabe", "kenji.w@example.com", "+1-555-0106"),
    ("Elena Rossi", "elena.r@example.com", "+1-555-0107"),
    ("Sam Thompson", "sam.t@example.com", "+1-555-0108"),
]

FIRST_NAMES = [
    "Aditi",
    "Lucas",
    "Mette",
    "Omar",
    "Sofia",
    "Ivan",
    "Nadia",
    "Rafael",
    "Lena",
    "Bo",
    "Maya",
    "Jon",
]

LAST_NAMES = [
    "Berg",
    "Costa",
    "Duarte",
    "Fischer",
    "Garcia",
    "Hansen",
    "Ibrahim",
    "Kovacs",
    "Lindgren",
    "Moreau",
    "Nakamura",
    "Olsen",
]


@dataclass(frozen=True)
class TenantSpec:
    slug: str
    name: str
    plan_code: str
    region: str
    branding: dict[str, Any]
    rng_seed: int
    members: list[tuple[str, str, str]]
    trains: list[dict[str, Any]]
    forward_bookings: int
    history_bookings: int


TENANT_SPECS: tuple[TenantSpec, ...] = (
    TenantSpec(
        slug=DEMO_SLUG,
        name="Demo Rail Co",
        plan_code="growth",
        region="us-east",
        branding={
            "primary_color": "#6d5efc",
            "accent_color": "#22d3ee",
            "support_email": "support@demo.railway",
            "logo_text": "Demo Rail",
        },
        rng_seed=42,
        members=DEMO_MEMBERS,
        trains=DEMO_TRAINS,
        forward_bookings=16,
        history_bookings=32,
    ),
    TenantSpec(
        slug="northline",
        name="Northline Rail",
        plan_code="enterprise",
        region="eu-west",
        branding={
            "primary_color": "#f97316",
            "accent_color": "#0ea5e9",
            "support_email": "support@northline.demo",
            "logo_text": "Northline",
        },
        rng_seed=7,
        members=NORTHLINE_MEMBERS,
        trains=NORTHLINE_TRAINS,
        forward_bookings=20,
        history_bookings=36,
    ),
    TenantSpec(
        slug="starter",
        name="Starter Junction",
        plan_code="starter",
        region="ap-southeast",
        branding={
            "primary_color": "#16a34a",
            "accent_color": "#facc15",
            "support_email": "support@starter.demo",
            "logo_text": "Starter Junction",
        },
        rng_seed=13,
        members=STARTER_MEMBERS,
        trains=STARTER_TRAINS,
        forward_bookings=3,
        history_bookings=3,
    ),
)


def _passenger_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


async def _seed_tenant(db, spec: TenantSpec) -> None:
    tenant = Tenant(
        slug=spec.slug,
        name=spec.name,
        plan_code=spec.plan_code,
        branding=spec.branding,
        region=spec.region,
    )
    db.add(tenant)
    await db.flush()
    await set_tenant_context(db, tenant.id)

    members: list[Member] = []
    for email, full_name, role in spec.members:
        member = Member(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=full_name,
            role=role,
        )
        db.add(member)
        members.append(member)
    await db.flush()

    trains: list[Train] = []
    for spec_row in spec.trains:
        train = Train(
            tenant_id=tenant.id,
            currency="USD",
            days_of_week=ALL_DAYS,
            **spec_row,
        )
        db.add(train)
        trains.append(train)
    await db.flush()

    plan = await get_plan(db, tenant.plan_code)
    entitlements = resolve_entitlements(
        plan.features if plan else {},
        plan.quotas if plan else {},
        tenant.features_override,
    )
    owner = members[0]

    rng = random.Random(spec.rng_seed)
    today = date.today()

    # Forward bookings through the real service keep inventory + audit honest.
    forward: list[Booking] = []
    for index in range(spec.forward_bookings):
        train = trains[index % len(trains)]
        travel_date = today + timedelta(days=rng.randint(0, 27))
        seats = rng.randint(1, 3)
        contact = CONTACTS[index % len(CONTACTS)]
        forward.append(
            await create_booking(
                db,
                tenant_id=tenant.id,
                entitlements=entitlements,
                actor=owner,
                data=BookingCreate(
                    train_id=train.id,
                    travel_date=travel_date,
                    seats=seats,
                    contact_name=contact[0],
                    contact_email=contact[1],
                    contact_phone=contact[2],
                    passengers=[
                        PassengerIn(full_name=_passenger_name(rng), age=rng.randint(2, 79))
                        for _ in range(seats)
                    ],
                    channel=rng.choice(CHANNELS),
                ),
                ip="seed",
            )
        )

    # Deterministic ~25% cancellation rate for the forward ledger.
    for index in range(0, len(forward), 4):
        await cancel_booking(
            db,
            tenant_id=tenant.id,
            actor=owner,
            booking_id=forward[index].id,
            ip="seed",
        )

    # Backdated history for reports, spread across the last 60 days.
    now = datetime.now(UTC)
    for index in range(spec.history_bookings):
        train = trains[(index + 2) % len(trains)]
        created = now - timedelta(
            days=rng.randint(1, 60), hours=rng.randint(0, 20)
        )
        max_travel_offset = max(0, min(4, (today - created.date()).days))
        travel_date = created.date() + timedelta(
            days=rng.randint(0, max_travel_offset)
        )
        seats = rng.randint(1, 4)
        contact = CONTACTS[(index + 3) % len(CONTACTS)]
        cancelled = index % 6 == 5
        refund_age_cutoff = now - timedelta(days=14)
        booking = Booking(
            tenant_id=tenant.id,
            pnr=_generate_pnr(),
            train_id=train.id,
            travel_date=travel_date,
            contact_name=contact[0],
            contact_email=contact[1],
            contact_phone=contact[2],
            seats=seats,
            status="cancelled" if cancelled else "confirmed",
            total_fare_cents=seats * train.fare_cents,
            currency="USD",
            channel=rng.choice(CHANNELS),
            refund_status=(
                ("processed" if created < refund_age_cutoff else "pending")
                if cancelled
                else "none"
            ),
            cancelled_at=created + timedelta(hours=6) if cancelled else None,
            created_by=owner.id,
            created_at=created,
            updated_at=created,
        )
        db.add(booking)
        await db.flush()
        for _ in range(seats):
            db.add(
                BookingPassenger(
                    tenant_id=tenant.id,
                    booking_id=booking.id,
                    full_name=_passenger_name(rng),
                    age=rng.randint(2, 79),
                )
            )

    await db.flush()


async def seed_all(db) -> dict[str, bool]:
    """Seed every workspace that does not exist yet. Returns slug -> created."""
    await ensure_plans(db)
    created: dict[str, bool] = {}
    for spec in TENANT_SPECS:
        if await get_tenant_by_slug(db, spec.slug) is not None:
            created[spec.slug] = False
            continue
        await _seed_tenant(db, spec)
        created[spec.slug] = True
    return created


async def main() -> None:
    async with async_session_maker() as session:
        created = await seed_all(session)
        await session.commit()
    fresh = [slug for slug, was_created in created.items() if was_created]
    if fresh:
        print(f"Seeded workspaces: {', '.join(fresh)} (staff password: {DEMO_PASSWORD})")
    else:
        print("All demo workspaces already exist; nothing to do.")


if __name__ == "__main__":
    asyncio.run(main())
