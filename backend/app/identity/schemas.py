import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$")
RESERVED_SLUGS = {
    "www", "api", "app", "admin", "dashboard", "mail", "status", "docs",
    "billing", "support", "static", "cdn", "assets",
}


def normalize_slug(value: str) -> str:
    value = value.strip().lower()
    if not SLUG_RE.match(value):
        raise ValueError(
            "Slug must be 3-32 characters: lowercase letters, numbers, and hyphens "
            "(cannot start or end with a hyphen)."
        )
    if value in RESERVED_SLUGS:
        raise ValueError("This slug is reserved.")
    return value


class RegisterRequest(BaseModel):
    org_name: str = Field(min_length=2, max_length=120)
    slug: str
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        return normalize_slug(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class MemberBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(owner|admin|manager|agent|viewer)$")


class MemberCreate(MemberBase):
    password: str | None = Field(default=None, min_length=8, max_length=128)


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, pattern="^(owner|admin|manager|agent|viewer)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    custom_domain: str | None
    status: str
    plan_code: str
    branding: dict[str, Any]
    default_currency: str
    locale: str
    timezone: str
    region: str


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    branding: dict[str, Any] | None = None
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    custom_domain: str | None = Field(default=None, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MemberOut
    tenant: TenantOut


class MeResponse(BaseModel):
    user: MemberOut
    tenant: TenantOut
    entitlements: dict[str, Any]
