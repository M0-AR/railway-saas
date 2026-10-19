import csv
import io
import secrets
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import record_audit
from app.bookings.models import Booking, BookingPassenger
from app.bookings.schemas import BookingCreate, PassengerIn
from app.core.csvutil import csv_cell
from app.core.errors import ConflictError, NotFoundError
from app.identity.entitlements import Entitlements, check_quota
from app.identity.models import Member
from app.trains.models import Train, TrainInventory

PNR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PNR_LENGTH = 6


def _generate_pnr() -> str:
    return "".join(secrets.choice(PNR_ALPHABET) for _ in range(PNR_LENGTH))


async def _ensure_inventory_row(
    db: AsyncSession, *, tenant_id: uuid.UUID, train_id: uuid.UUID, travel_date: date
) -> None:
    await db.execute(
        pg_insert(TrainInventory)
        .values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            train_id=train_id,
            travel_date=travel_date,
            seats_booked=0,
        )
        .on_conflict_do_nothing(
            index_elements=["tenant_id", "train_id", "travel_date"]
        )
    )


async def _locked_inventory(
    db: AsyncSession, *, tenant_id: uuid.UUID, train_id: uuid.UUID, travel_date: date
) -> TrainInventory:
    result = await db.execute(
        select(TrainInventory)
        .where(
            TrainInventory.tenant_id == tenant_id,
            TrainInventory.train_id == train_id,
            TrainInventory.travel_date == travel_date,
        )
        .with_for_update()
    )
    return result.scalar_one()


async def create_booking(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    entitlements: Entitlements,
    actor: Member,
    data: BookingCreate,
    ip: str = "",
) -> Booking:
    if data.passengers and len(data.passengers) != data.seats:
        raise ConflictError(
            f"Passenger count ({len(data.passengers)}) must equal seat count ({data.seats})."
        )

    await db.execute(
        select(
            func.pg_advisory_xact_lock(
                func.hashtext(f"booking-quota:{tenant_id}")
            )
        )
    )
    month_start = datetime.now(UTC).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    created_this_month = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Booking)
                .where(Booking.tenant_id == tenant_id, Booking.created_at >= month_start)
            )
        ).scalar_one()
    )
    check_quota(entitlements, "max_bookings_per_month", created_this_month)

    train = (
        await db.execute(
            select(Train).where(Train.id == data.train_id, Train.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if train is None:
        raise NotFoundError("Train not found.")
    if not train.is_active:
        raise ConflictError("This train is no longer in service.")

    if data.travel_date < date.today():
        raise ConflictError("Travel date cannot be in the past.")
    if data.travel_date.isoweekday() not in (train.days_of_week or []):
        raise ConflictError(
            f"{train.name} does not operate on {data.travel_date.strftime('%A')}s."
        )

    await _ensure_inventory_row(
        db, tenant_id=tenant_id, train_id=train.id, travel_date=data.travel_date
    )
    inventory = await _locked_inventory(
        db, tenant_id=tenant_id, train_id=train.id, travel_date=data.travel_date
    )

    seats_left = train.total_seats - inventory.seats_booked
    if data.seats > seats_left:
        raise ConflictError(
            f"Only {max(0, seats_left)} seat(s) left for that date.",
            details={"seats_left": max(0, seats_left), "requested": data.seats},
        )

    inventory.seats_booked += data.seats
    inventory.updated_at = datetime.now(UTC)

    booking: Booking | None = None
    for _ in range(6):
        candidate = Booking(
            tenant_id=tenant_id,
            pnr=_generate_pnr(),
            train_id=train.id,
            travel_date=data.travel_date,
            contact_name=data.contact_name,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            seats=data.seats,
            status="confirmed",
            total_fare_cents=data.seats * train.fare_cents,
            currency=train.currency,
            channel=data.channel,
            notes=data.notes,
            created_by=actor.id,
        )
        try:
            async with db.begin_nested():
                db.add(candidate)
            booking = candidate
            break
        except IntegrityError:
            booking = None
            continue
    if booking is None:
        raise ConflictError("Could not allocate a booking reference. Please retry.")

    passenger_sources: list[PassengerIn] = (
        data.passengers
        if data.passengers
        else [PassengerIn(full_name=data.contact_name) for _ in range(data.seats)]
    )
    for source in passenger_sources[: data.seats]:
        db.add(
            BookingPassenger(
                tenant_id=tenant_id,
                booking_id=booking.id,
                full_name=source.full_name,
                age=source.age,
                gender=source.gender,
                seat_preference=source.seat_preference,
                id_document=source.id_document,
            )
        )

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="booking.created",
        entity_type="booking",
        entity_id=str(booking.id),
        payload={
            "pnr": booking.pnr,
            "train": train.number,
            "travel_date": str(data.travel_date),
            "seats": data.seats,
            "total_fare_cents": booking.total_fare_cents,
        },
        ip=ip,
    )
    await db.flush()

    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.passengers), selectinload(Booking.train))
        .where(Booking.id == booking.id, Booking.tenant_id == tenant_id)
    )
    return result.scalar_one()


async def get_booking(
    db: AsyncSession, *, tenant_id: uuid.UUID, booking_id: uuid.UUID
) -> Booking:
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.passengers), selectinload(Booking.train))
        .where(Booking.id == booking_id, Booking.tenant_id == tenant_id)
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        raise NotFoundError("Booking not found.")
    return booking


async def list_bookings(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    q: str | None,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
    train_id: uuid.UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[tuple[Booking, Train]], int]:
    conditions = [Booking.tenant_id == tenant_id]
    if q:
        pattern = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(Booking.pnr).like(pattern),
                func.lower(Booking.contact_name).like(pattern),
                func.lower(Booking.contact_email).like(pattern),
                func.lower(Booking.contact_phone).like(pattern),
            )
        )
    if status:
        conditions.append(Booking.status == status)
    if date_from:
        conditions.append(Booking.travel_date >= date_from)
    if date_to:
        conditions.append(Booking.travel_date <= date_to)
    if train_id:
        conditions.append(Booking.train_id == train_id)

    stmt = (
        select(Booking, Train)
        .join(Train, Train.id == Booking.train_id)
        .where(*conditions)
        .order_by(Booking.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(Booking).where(*conditions)
    rows = list((await db.execute(stmt)).all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return rows, total


async def cancel_booking(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor: Member,
    booking_id: uuid.UUID,
    ip: str = "",
) -> Booking:
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.passengers), selectinload(Booking.train))
        .where(Booking.id == booking_id, Booking.tenant_id == tenant_id)
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    if booking is None:
        raise NotFoundError("Booking not found.")
    if booking.status == "cancelled":
        raise ConflictError("This booking is already cancelled.")

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(UTC)
    booking.cancelled_by = actor.id
    booking.refund_status = "pending"

    await _ensure_inventory_row(
        db, tenant_id=tenant_id, train_id=booking.train_id, travel_date=booking.travel_date
    )
    inventory = await _locked_inventory(
        db, tenant_id=tenant_id, train_id=booking.train_id, travel_date=booking.travel_date
    )
    inventory.seats_booked = max(0, inventory.seats_booked - booking.seats)
    inventory.updated_at = datetime.now(UTC)

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="booking.cancelled",
        entity_type="booking",
        entity_id=str(booking.id),
        payload={"pnr": booking.pnr, "seats": booking.seats},
        ip=ip,
    )
    await db.flush()
    return booking


async def all_bookings_for_export(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[tuple[Booking, Train]]:
    rows = (
        await db.execute(
            select(Booking, Train)
            .join(Train, Train.id == Booking.train_id)
            .where(Booking.tenant_id == tenant_id)
            .order_by(Booking.created_at.desc())
        )
    ).all()
    return list(rows)


def export_bookings_csv(rows: list[tuple[Booking, Train]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "pnr", "train_number", "train_name", "travel_date", "contact_name",
            "contact_email", "contact_phone", "seats", "status", "total_fare",
            "currency", "channel", "refund_status", "created_at",
        ]
    )
    for booking, train in rows:
        writer.writerow(
            [
                csv_cell(v)
                for v in [
                    booking.pnr,
                    train.number,
                    train.name,
                    booking.travel_date.isoformat(),
                    booking.contact_name,
                    booking.contact_email,
                    booking.contact_phone,
                    booking.seats,
                    booking.status,
                    f"{booking.total_fare_cents / 100:.2f}",
                    booking.currency,
                    booking.channel,
                    booking.refund_status,
                    booking.created_at.isoformat(),
                ]
            ]
        )
    return buffer.getvalue()
