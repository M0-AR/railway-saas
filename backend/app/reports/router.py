import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookings.models import Booking
from app.db.session import get_session
from app.identity.dependencies import AuthContext, require_feature
from app.trains.models import Train, TrainInventory

router = APIRouter()


class RevenueSummary(BaseModel):
    today_cents: int
    last_30d_cents: int


class BookingsSummary(BaseModel):
    today: int
    last_30d: int


class TrainsSummary(BaseModel):
    active: int
    total: int


class OccupancySummary(BaseModel):
    booked: int
    capacity: int
    rate: float


class OverviewOut(BaseModel):
    currency: str
    revenue: RevenueSummary
    bookings: BookingsSummary
    trains: TrainsSummary
    occupancy_today: OccupancySummary
    cancellation_rate_30d: float


class RevenuePoint(BaseModel):
    day: date
    revenue_cents: int
    bookings: int


class RevenueOut(BaseModel):
    currency: str
    days: list[RevenuePoint]


class TopTrainRow(BaseModel):
    train_id: uuid.UUID
    number: str
    name: str
    bookings: int
    seats: int
    revenue_cents: int


class TopTrainsOut(BaseModel):
    days: int
    currency: str
    trains: list[TopTrainRow]


class OccupancyRow(BaseModel):
    train_id: uuid.UUID
    number: str
    name: str
    booked: int
    capacity: int
    rate: float


class OccupancyOut(BaseModel):
    date: date
    trains: list[OccupancyRow]


def _start_of_today() -> datetime:
    today = datetime.now(UTC).date()
    return datetime(today.year, today.month, today.day, tzinfo=UTC)


async def _scalar(db: AsyncSession, stmt) -> int:
    value = (await db.execute(stmt)).scalar()
    return int(value or 0)


@router.get("/overview", response_model=OverviewOut)
async def overview(
    ctx: AuthContext = Depends(require_feature("reports.basic")),
    db: AsyncSession = Depends(get_session),
):
    tenant_id = ctx.tenant.id
    now = datetime.now(UTC)
    start_today = _start_of_today()
    start_30d = now - timedelta(days=30)
    today = now.date()

    confirmed = (Booking.tenant_id == tenant_id, Booking.status == "confirmed")

    revenue_today = await _scalar(
        db,
        select(func.coalesce(func.sum(Booking.total_fare_cents), 0)).where(
            *confirmed, Booking.created_at >= start_today
        ),
    )
    revenue_30d = await _scalar(
        db,
        select(func.coalesce(func.sum(Booking.total_fare_cents), 0)).where(
            *confirmed, Booking.created_at >= start_30d
        ),
    )
    bookings_today = await _scalar(
        db,
        select(func.count()).select_from(Booking).where(
            Booking.tenant_id == tenant_id, Booking.created_at >= start_today
        ),
    )
    bookings_30d = await _scalar(
        db,
        select(func.count()).select_from(Booking).where(
            Booking.tenant_id == tenant_id, Booking.created_at >= start_30d
        ),
    )
    trains_active = await _scalar(
        db,
        select(func.count()).select_from(Train).where(
            Train.tenant_id == tenant_id, Train.is_active.is_(True)
        ),
    )
    trains_total = await _scalar(
        db, select(func.count()).select_from(Train).where(Train.tenant_id == tenant_id)
    )

    occupancy_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(TrainInventory.seats_booked), 0),
                func.coalesce(func.sum(Train.total_seats), 0),
            )
            .select_from(Train)
            .join(
                TrainInventory,
                (TrainInventory.train_id == Train.id)
                & (TrainInventory.travel_date == today),
                isouter=True,
            )
            .where(Train.tenant_id == tenant_id, Train.is_active.is_(True))
        )
    ).one()
    booked = int(occupancy_row[0] or 0)
    capacity = int(occupancy_row[1] or 0)

    cancelled_30d = await _scalar(
        db,
        select(func.count()).select_from(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.created_at >= start_30d,
            Booking.status == "cancelled",
        ),
    )
    cancellation_rate = (cancelled_30d / bookings_30d) if bookings_30d else 0.0

    return OverviewOut(
        currency=ctx.tenant.default_currency,
        revenue=RevenueSummary(today_cents=revenue_today, last_30d_cents=revenue_30d),
        bookings=BookingsSummary(today=bookings_today, last_30d=bookings_30d),
        trains=TrainsSummary(active=trains_active, total=trains_total),
        occupancy_today=OccupancySummary(
            booked=booked, capacity=capacity, rate=round(booked / capacity, 4) if capacity else 0.0
        ),
        cancellation_rate_30d=round(cancellation_rate, 4),
    )


@router.get("/revenue", response_model=RevenueOut)
async def revenue_series(
    days: int = Query(30, ge=7, le=180),
    ctx: AuthContext = Depends(require_feature("reports.advanced")),
    db: AsyncSession = Depends(get_session),
):
    now = datetime.now(UTC)
    start = now - timedelta(days=days - 1)
    start_day = datetime(start.year, start.month, start.day, tzinfo=UTC)

    day_expr = cast(Booking.created_at, Date)
    rows = (
        await db.execute(
            select(
                day_expr.label("day"),
                func.coalesce(func.sum(Booking.total_fare_cents), 0),
                func.count(),
            )
            .where(
                Booking.tenant_id == ctx.tenant.id,
                Booking.status == "confirmed",
                Booking.created_at >= start_day,
            )
            .group_by(day_expr)
        )
    ).all()
    by_day = {row[0]: (int(row[1]), int(row[2])) for row in rows}

    series: list[RevenuePoint] = []
    for offset in range(days):
        day = start_day.date() + timedelta(days=offset)
        revenue_cents, bookings = by_day.get(day, (0, 0))
        series.append(RevenuePoint(day=day, revenue_cents=revenue_cents, bookings=bookings))

    return RevenueOut(currency=ctx.tenant.default_currency, days=series)


@router.get("/top-trains", response_model=TopTrainsOut)
async def top_trains(
    days: int = Query(30, ge=7, le=180),
    ctx: AuthContext = Depends(require_feature("reports.advanced")),
    db: AsyncSession = Depends(get_session),
):
    start = datetime.now(UTC) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                Train.id,
                Train.number,
                Train.name,
                func.count(Booking.id),
                func.coalesce(func.sum(Booking.seats), 0),
                func.coalesce(func.sum(Booking.total_fare_cents), 0),
            )
            .join(Booking, Booking.train_id == Train.id)
            .where(
                Train.tenant_id == ctx.tenant.id,
                Booking.status == "confirmed",
                Booking.created_at >= start,
            )
            .group_by(Train.id, Train.number, Train.name)
            .order_by(func.coalesce(func.sum(Booking.total_fare_cents), 0).desc())
            .limit(10)
        )
    ).all()
    return TopTrainsOut(
        days=days,
        currency=ctx.tenant.default_currency,
        trains=[
            TopTrainRow(
                train_id=row[0],
                number=row[1],
                name=row[2],
                bookings=int(row[3]),
                seats=int(row[4]),
                revenue_cents=int(row[5]),
            )
            for row in rows
        ],
    )


@router.get("/occupancy", response_model=OccupancyOut)
async def occupancy(
    on: date | None = None,
    ctx: AuthContext = Depends(require_feature("reports.advanced")),
    db: AsyncSession = Depends(get_session),
):
    target = on or datetime.now(UTC).date()
    rows = (
        await db.execute(
            select(
                Train.id,
                Train.number,
                Train.name,
                Train.total_seats,
                func.coalesce(func.sum(TrainInventory.seats_booked), 0),
            )
            .join(
                TrainInventory,
                (TrainInventory.train_id == Train.id)
                & (TrainInventory.travel_date == target),
                isouter=True,
            )
            .where(Train.tenant_id == ctx.tenant.id, Train.is_active.is_(True))
            .group_by(Train.id, Train.number, Train.name, Train.total_seats)
        )
    ).all()

    trains = [
        OccupancyRow(
            train_id=row[0],
            number=row[1],
            name=row[2],
            booked=int(row[4]),
            capacity=int(row[3]),
            rate=round(int(row[4]) / int(row[3]), 4) if int(row[3]) else 0.0,
        )
        for row in rows
    ]
    trains.sort(key=lambda item: item.rate, reverse=True)
    return OccupancyOut(date=target, trains=trains)
