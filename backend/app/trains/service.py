import csv
import io
import uuid
from datetime import date, time, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.bookings.models import Booking
from app.core.csvutil import csv_cell
from app.core.errors import AppError, ConflictError, NotFoundError
from app.identity.entitlements import Entitlements, check_quota
from app.identity.models import Member
from app.trains.models import Train, TrainInventory
from app.trains.schemas import AvailabilityDay, AvailabilityOut, TrainCreate, TrainUpdate

TRAIN_TYPES = {"express", "intercity", "regional", "high_speed", "sleeper", "commuter"}


async def list_trains(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    q: str | None,
    train_type: str | None,
    is_active: bool | None,
    offset: int,
    limit: int,
) -> tuple[list[Train], int]:
    conditions = [Train.tenant_id == tenant_id]
    if q:
        pattern = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(Train.number).like(pattern),
                func.lower(Train.name).like(pattern),
                func.lower(Train.source).like(pattern),
                func.lower(Train.destination).like(pattern),
            )
        )
    if train_type:
        conditions.append(Train.train_type == train_type)
    if is_active is not None:
        conditions.append(Train.is_active == is_active)

    stmt = (
        select(Train)
        .where(*conditions)
        .order_by(Train.number.asc())
        .offset(offset)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(Train).where(*conditions)
    trains = list((await db.execute(stmt)).scalars().all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return trains, total


async def get_train(db: AsyncSession, *, tenant_id: uuid.UUID, train_id: uuid.UUID) -> Train:
    result = await db.execute(
        select(Train).where(Train.id == train_id, Train.tenant_id == tenant_id)
    )
    train = result.scalar_one_or_none()
    if train is None:
        raise NotFoundError("Train not found.")
    return train


async def create_train(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    default_currency: str,
    entitlements: Entitlements,
    actor: Member,
    data: TrainCreate,
    ip: str = "",
) -> Train:
    current = int(
        (
            await db.execute(
                select(func.count()).select_from(Train).where(Train.tenant_id == tenant_id)
            )
        ).scalar_one()
    )
    check_quota(entitlements, "max_trains", current)

    clash = await db.execute(
        select(Train.id).where(Train.tenant_id == tenant_id, Train.number == data.number)
    )
    if clash.scalar_one_or_none() is not None:
        raise ConflictError(f"Train number {data.number} already exists in this workspace.")

    payload = data.model_dump()
    payload["stops"] = [s if isinstance(s, dict) else s.model_dump() for s in payload["stops"]]
    train = Train(
        tenant_id=tenant_id,
        currency=(payload.pop("currency") or default_currency).upper(),
        **payload,
    )
    try:
        async with db.begin_nested():
            db.add(train)
    except IntegrityError as exc:
        raise ConflictError(f"Train number {data.number} already exists.") from exc

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="train.created",
        entity_type="train",
        entity_id=str(train.id),
        payload={"number": train.number, "name": train.name},
        ip=ip,
    )
    return train


async def update_train(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor: Member,
    train_id: uuid.UUID,
    data: TrainUpdate,
    ip: str = "",
) -> Train:
    train = await get_train(db, tenant_id=tenant_id, train_id=train_id)
    updates = data.model_dump(exclude_unset=True)

    if "number" in updates and updates["number"] != train.number:
        clash = await db.execute(
            select(Train.id).where(
                Train.tenant_id == tenant_id,
                Train.number == updates["number"],
                Train.id != train_id,
            )
        )
        if clash.scalar_one_or_none() is not None:
            raise ConflictError(f"Train number {updates['number']} already exists.")

    if updates.get("total_seats") is not None and updates["total_seats"] < train.total_seats:
        booked = int(
            (
                await db.execute(
                    select(func.coalesce(func.max(TrainInventory.seats_booked), 0)).where(
                        TrainInventory.tenant_id == tenant_id,
                        TrainInventory.train_id == train_id,
                    )
                )
            ).scalar_one()
        )
        if updates["total_seats"] < booked:
            raise ConflictError(
                f"Cannot reduce capacity below already-booked seats ({booked})."
            )

    if "stops" in updates and updates["stops"] is not None:
        updates["stops"] = [
            s if isinstance(s, dict) else s.model_dump() for s in updates["stops"]
        ]
    if updates.get("currency"):
        updates["currency"] = updates["currency"].upper()

    for key, value in updates.items():
        setattr(train, key, value)

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="train.updated",
        entity_type="train",
        entity_id=str(train.id),
        payload={k: str(v) for k, v in updates.items()},
        ip=ip,
    )
    return train


async def archive_or_delete_train(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor: Member,
    train_id: uuid.UUID,
    ip: str = "",
) -> dict:
    train = await get_train(db, tenant_id=tenant_id, train_id=train_id)

    booking_count = int(
        (
            await db.execute(
                select(func.count()).select_from(Booking).where(
                    Booking.tenant_id == tenant_id, Booking.train_id == train_id
                )
            )
        ).scalar_one()
    )

    if booking_count > 0:
        train.is_active = False
        action = "train.archived"
        result = {"deleted": False, "archived": True, "bookings": booking_count}
    else:
        await db.delete(train)
        action = "train.deleted"
        result = {"deleted": True, "archived": False, "bookings": 0}

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action=action,
        entity_type="train",
        entity_id=str(train_id),
        payload={"number": train.number, "name": train.name},
        ip=ip,
    )
    return result


async def availability(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    train_id: uuid.UUID,
    date_from: date,
    days: int = 14,
) -> AvailabilityOut:
    train = await get_train(db, tenant_id=tenant_id, train_id=train_id)
    date_to = date_from + timedelta(days=days - 1)

    rows = (
        await db.execute(
            select(TrainInventory.travel_date, TrainInventory.seats_booked).where(
                TrainInventory.tenant_id == tenant_id,
                TrainInventory.train_id == train_id,
                TrainInventory.travel_date >= date_from,
                TrainInventory.travel_date <= date_to,
            )
        )
    ).all()
    booked_by_date = {row[0]: row[1] for row in rows}

    result: list[AvailabilityDay] = []
    for offset in range(days):
        day = date_from + timedelta(days=offset)
        runs = day.isoweekday() in (train.days_of_week or [])
        booked = booked_by_date.get(day, 0)
        result.append(
            AvailabilityDay(
                date=day,
                runs=runs,
                seats_left=max(0, train.total_seats - booked) if runs else 0,
            )
        )
    return AvailabilityOut(train_id=train.id, total_seats=train.total_seats, days=result)


# ------------------------------------------------------------------ CSV import

CSV_REQUIRED = {"number", "name", "source", "destination", "total_seats", "fare"}


def _parse_int(value: str, field: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{field}' must be a whole number.") from exc


def _parse_fare_cents(value: str) -> int:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("'fare' must be a number, e.g. 24.50") from exc
    if amount < 0:
        raise ValueError("'fare' cannot be negative.")
    return int((amount * 100).quantize(Decimal("1")))


def _parse_time(value: str | None) -> time | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return time.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError("Time must look like 14:30 (HH:MM).") from exc


def _parse_days(value: str | None) -> list[int]:
    if value is None or str(value).strip() == "":
        return [1, 2, 3, 4, 5, 6, 7]
    try:
        days = sorted({int(part.strip()) for part in str(value).split(",") if part.strip()})
    except ValueError as exc:
        raise ValueError("'days_of_week' must look like 1,2,3,4,5 (1=Mon..7=Sun).") from exc
    if not days or any(d < 1 or d > 7 for d in days):
        raise ValueError("'days_of_week' values must be between 1 and 7.")
    return days


async def import_trains_csv(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    default_currency: str,
    entitlements: Entitlements,
    actor: Member,
    raw: bytes,
    ip: str = "",
) -> dict:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError("File must be UTF-8 encoded CSV.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise AppError("CSV file has no header row.")
    fieldnames = [f.strip().lower() for f in reader.fieldnames]
    missing = CSV_REQUIRED - set(fieldnames)
    if missing:
        raise AppError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    reader.fieldnames = fieldnames

    existing_rows = (
        await db.execute(select(Train).where(Train.tenant_id == tenant_id))
    ).scalars().all()
    existing = {t.number: t for t in existing_rows}

    parsed: list[dict] = []
    errors: list[dict] = []
    new_numbers: set[str] = set()
    for line_no, row in enumerate(reader, start=2):
        try:
            number = str(row.get("number", "")).strip()
            if not number:
                raise ValueError("'number' is required.")
            train_type = str(row.get("train_type") or row.get("type") or "express").strip().lower()
            if train_type not in TRAIN_TYPES:
                raise ValueError(f"'train_type' must be one of: {', '.join(sorted(TRAIN_TYPES))}")
            parsed.append(
                {
                    "line": line_no,
                    "number": number,
                    "name": str(row.get("name", "")).strip(),
                    "train_type": train_type,
                    "source": str(row.get("source", "")).strip(),
                    "destination": str(row.get("destination", "")).strip(),
                    "departure_time": _parse_time(row.get("departure_time")),
                    "arrival_time": _parse_time(row.get("arrival_time")),
                    "days_of_week": _parse_days(row.get("days_of_week")),
                    "total_seats": _parse_int(row.get("total_seats"), "total_seats"),
                    "fare_cents": _parse_fare_cents(row.get("fare")),
                }
            )
            if number not in existing:
                new_numbers.add(number)
        except ValueError as exc:
            errors.append({"line": line_no, "error": str(exc)})

    check_quota(entitlements, "max_trains", len(existing) + len(new_numbers))

    created = 0
    updated = 0
    for item in parsed:
        number = item["number"]
        values = {
            k: v
            for k, v in item.items()
            if k not in ("line", "number")
        }
        try:
            if number in existing:
                train = existing[number]
                for key, value in values.items():
                    setattr(train, key, value)
                updated += 1
            else:
                train = Train(
                    tenant_id=tenant_id,
                    number=number,
                    currency=default_currency,
                    **values,
                )
                async with db.begin_nested():
                    db.add(train)
                existing[number] = train
                created += 1
        except IntegrityError:
            errors.append({"line": item["line"], "error": "Duplicate train number."})

    await record_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        action="trains.imported",
        entity_type="train",
        payload={"created": created, "updated": updated, "failed": len(errors)},
        ip=ip,
    )
    return {"created": created, "updated": updated, "errors": errors}


def export_trains_csv(trains: list[Train]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "number", "name", "train_type", "source", "destination",
            "departure_time", "arrival_time", "days_of_week", "total_seats",
            "fare", "currency", "is_active",
        ]
    )
    for t in trains:
        writer.writerow(
            [
                csv_cell(v)
                for v in [
                    t.number,
                    t.name,
                    t.train_type,
                    t.source,
                    t.destination,
                    t.departure_time.isoformat() if t.departure_time else "",
                    t.arrival_time.isoformat() if t.arrival_time else "",
                    ",".join(str(d) for d in (t.days_of_week or [])),
                    t.total_seats,
                    f"{t.fare_cents / 100:.2f}",
                    t.currency,
                    "yes" if t.is_active else "no",
                ]
            ]
        )
    return buffer.getvalue()


async def all_trains_for_export(db: AsyncSession, tenant_id: uuid.UUID) -> list[Train]:
    rows = (
        await db.execute(
            select(Train).where(Train.tenant_id == tenant_id).order_by(Train.number.asc())
        )
    ).scalars().all()
    return list(rows)
