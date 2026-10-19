import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, clamp_page
from app.core.request import client_ip
from app.db.session import get_session
from app.identity.dependencies import AuthContext, require_feature, require_roles
from app.trains import service
from app.trains.schemas import (
    AvailabilityOut,
    ImportResult,
    TrainCreate,
    TrainOut,
    TrainUpdate,
)

router = APIRouter()


@router.get("", response_model=Page[TrainOut])
async def list_trains(
    q: str | None = None,
    train_type: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager", "agent", "viewer")),
    db: AsyncSession = Depends(get_session),
):
    page, page_size, offset = clamp_page(page, page_size)
    trains, total = await service.list_trains(
        db,
        tenant_id=ctx.tenant.id,
        q=q,
        train_type=train_type,
        is_active=is_active,
        offset=offset,
        limit=page_size,
    )
    return Page(
        items=[TrainOut.model_validate(t) for t in trains],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export.csv")
async def export_trains(
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager")),
    db: AsyncSession = Depends(get_session),
):
    trains = await service.all_trains_for_export(db, ctx.tenant.id)
    csv_text = service.export_trains_csv(trains)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trains.csv"},
    )


@router.post("", response_model=TrainOut, status_code=status.HTTP_201_CREATED)
async def create_train(
    payload: TrainCreate,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager")),
    db: AsyncSession = Depends(get_session),
):
    train = await service.create_train(
        db,
        tenant_id=ctx.tenant.id,
        default_currency=ctx.tenant.default_currency,
        entitlements=ctx.entitlements,
        actor=ctx.member,
        data=payload,
        ip=client_ip(request),
    )
    return TrainOut.model_validate(train)


@router.post("/import", response_model=ImportResult)
async def import_trains(
    request: Request,
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(require_feature("csv.import")),
    db: AsyncSession = Depends(get_session),
):
    if ctx.member.role not in ("owner", "admin", "manager"):
        from app.core.errors import ForbiddenError

        raise ForbiddenError("Your role does not allow importing trains.")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        from app.core.errors import AppError

        raise AppError("File too large (max 5 MB).")

    result = await service.import_trains_csv(
        db,
        tenant_id=ctx.tenant.id,
        default_currency=ctx.tenant.default_currency,
        entitlements=ctx.entitlements,
        actor=ctx.member,
        raw=raw,
        ip=client_ip(request),
    )
    return ImportResult(**result)


@router.get("/{train_id}", response_model=TrainOut)
async def get_train(
    train_id: uuid.UUID,
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager", "agent", "viewer")),
    db: AsyncSession = Depends(get_session),
):
    train = await service.get_train(db, tenant_id=ctx.tenant.id, train_id=train_id)
    return TrainOut.model_validate(train)


@router.patch("/{train_id}", response_model=TrainOut)
async def update_train(
    train_id: uuid.UUID,
    payload: TrainUpdate,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager")),
    db: AsyncSession = Depends(get_session),
):
    train = await service.update_train(
        db,
        tenant_id=ctx.tenant.id,
        actor=ctx.member,
        train_id=train_id,
        data=payload,
        ip=client_ip(request),
    )
    return TrainOut.model_validate(train)


@router.delete("/{train_id}")
async def delete_train(
    train_id: uuid.UUID,
    request: Request,
    ctx: AuthContext = Depends(require_roles("owner", "admin")),
    db: AsyncSession = Depends(get_session),
):
    return await service.archive_or_delete_train(
        db,
        tenant_id=ctx.tenant.id,
        actor=ctx.member,
        train_id=train_id,
        ip=client_ip(request),
    )


@router.get("/{train_id}/availability", response_model=AvailabilityOut)
async def train_availability(
    train_id: uuid.UUID,
    date_from: date | None = None,
    days: int = Query(14, ge=1, le=60),
    ctx: AuthContext = Depends(require_roles("owner", "admin", "manager", "agent", "viewer")),
    db: AsyncSession = Depends(get_session),
):
    return await service.availability(
        db,
        tenant_id=ctx.tenant.id,
        train_id=train_id,
        date_from=date_from or date.today(),
        days=days,
    )
