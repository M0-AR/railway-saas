import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk

if TYPE_CHECKING:
    from app.trains.models import Train


class Booking(Base, UUIDPk, Timestamps):
    __tablename__ = "booking"
    __table_args__ = (
        UniqueConstraint("tenant_id", "pnr", name="booking_tenant_pnr_key"),
        Index("booking_tenant_travel_date_idx", "tenant_id", "travel_date"),
        Index("booking_tenant_status_idx", "tenant_id", "status"),
        Index("booking_tenant_contact_idx", "tenant_id", "contact_email"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pnr: Mapped[str] = mapped_column(String(10), nullable=False)
    train_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("train.id", ondelete="RESTRICT"), nullable=False
    )
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    contact_phone: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="confirmed")
    total_fare_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    refund_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="counter")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column()
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column()

    train: Mapped["Train"] = relationship(lazy="raise")
    passengers: Mapped[list["BookingPassenger"]] = relationship(lazy="raise")


class BookingPassenger(Base, UUIDPk, Timestamps):
    __tablename__ = "booking_passenger"
    __table_args__ = (Index("booking_passenger_tenant_booking_idx", "tenant_id", "booking_id"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    seat_preference: Mapped[str] = mapped_column(String(24), nullable=False, default="")
    id_document: Mapped[str] = mapped_column(String(64), nullable=False, default="")
