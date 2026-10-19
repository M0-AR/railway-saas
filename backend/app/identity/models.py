import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk


class Plan(Base, Timestamps):
    __tablename__ = "plan"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    interval: Mapped[str] = mapped_column(String(16), nullable=False, default="month")
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    quotas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Tenant(Base, UUIDPk, Timestamps):
    __tablename__ = "tenant"

    slug: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    custom_domain: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    plan_code: Mapped[str] = mapped_column(
        ForeignKey("plan.code", ondelete="RESTRICT"), nullable=False, default="starter"
    )
    branding: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    features_override: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    region: Mapped[str] = mapped_column(String(32), nullable=False, default="global")
    billing_customer_id: Mapped[str | None] = mapped_column(String(64))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Member(Base, UUIDPk, Timestamps):
    __tablename__ = "member"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="member_tenant_email_key"),
        Index("member_tenant_role_idx", "tenant_id", "role"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="agent")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
