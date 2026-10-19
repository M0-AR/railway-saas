import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.bookings import service
from app.bookings.schemas import BookingCreate, BookingListOut, BookingOut
from app.core.pagination import Page, clamp_page
from app.core.request import client_ip
from app.db.session import get_session
from app.identity.dependencies import AuthContext, require_roles

router = APIRouter()

STAFF_ROLES = ("owner", "admin", "manager", "agent")


@router.get("", response_model=Page[BookingListOut])
async def list_bookings(
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    train_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager", "agent", "viewer")),
    db: AsyncSession = Depends(get_session),
):
    page, page_size, offset = clamp_page(page, page_size)
    rows, total = await service.list_bookings(
        db,
        tenant_id=ctx.tenant.id,
        q=q,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        train_id=train_id,
        offset=offset,
        limit=page_size,
    )
    items = [
        BookingListOut(
            id=booking.id,
            pnr=booking.pnr,
            train_number=train.number,
            train_name=train.name,
            travel_date=booking.travel_date,
            contact_name=booking.contact_name,
            seats=booking.seats,
            status=booking.status,
            total_fare_cents=booking.total_fare_cents,
            currency=booking.currency,
            channel=booking.channel,
            created_at=booking.created_at,
        )
        for booking, train in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/export.csv")
async def export_bookings(
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager")),
    db: AsyncSession = Depends(get_session),
):
    rows = await service.all_bookings_for_export(db, ctx.tenant.id)
    csv_text = service.export_bookings_csv(rows)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bookings.csv"},
    )


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager", "agent")),
    db: AsyncSession = Depends(get_session),
):
    booking = await service.create_booking(
        db,
        tenant_id=ctx.tenant.id,
        entitlements=ctx.entitlements,
        actor=ctx.member,
        data=payload,
        ip=client_ip(request),
    )
    return BookingOut.model_validate(booking)


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID,
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager", "agent", "viewer")),
    db: AsyncSession = Depends(get_session),
):
    booking = await service.get_booking(db, tenant_id=ctx.tenant.id, booking_id=booking_id)
    return BookingOut.model_validate(booking)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager", "agent")),
    db: AsyncSession = Depends(get_session),
):
    booking = await service.cancel_booking(
        db,
        tenant_id=ctx.tenant.id,
        actor=ctx.member,
        booking_id=booking_id,
        ip=client_ip(request),
    )
    return BookingOut.model_validate(booking)
