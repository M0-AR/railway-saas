import uuid
from datetime import date, time
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk


class Train(Base, UUIDPk, Timestamps):
    __tablename__ = "train"
    __table_args__ = (
        UniqueConstraint("tenant_id", "number", name="train_tenant_number_key"),
        Index("train_tenant_name_idx", "tenant_id", "name"),
        Index("train_tenant_route_idx", "tenant_id", "source", "destination"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    train_type: Mapped[str] = mapped_column(String(24), nullable=False, default="express")
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    departure_time: Mapped[time | None] = mapped_column(Time)
    arrival_time: Mapped[time | None] = mapped_column(Time)
    days_of_week: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=lambda: [1, 2, 3, 4, 5, 6, 7]
    )
    stops: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    fare_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TrainInventory(Base, UUIDPk, Timestamps):
    __tablename__ = "train_inventory"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "train_id", "travel_date", name="train_inventory_tenant_train_date_key"
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    train_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("train.id", ondelete="CASCADE"), nullable=False
    )
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    seats_booked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
