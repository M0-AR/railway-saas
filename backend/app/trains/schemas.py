import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

TRAIN_TYPE_PATTERN = "^(express|intercity|regional|high_speed|sleeper|commuter)$"


class Stop(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    offset_minutes: int = Field(ge=0, le=10000)


class TrainBase(BaseModel):
    number: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=120)
    train_type: str = Field(default="express", pattern=TRAIN_TYPE_PATTERN)
    source: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    departure_time: time | None = None
    arrival_time: time | None = None
    days_of_week: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    stops: list[Stop] = Field(default_factory=list)
    total_seats: int = Field(ge=1, le=2000)
    fare_cents: int = Field(ge=0, le=100_000_000)
    currency: str = Field(default="", max_length=3)

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("At least one operating day is required.")
        if any(day < 1 or day > 7 for day in v):
            raise ValueError("Days must be between 1 (Monday) and 7 (Sunday).")
        return sorted(set(v))


class TrainCreate(TrainBase):
    pass


class TrainUpdate(BaseModel):
    number: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    train_type: str | None = Field(default=None, pattern=TRAIN_TYPE_PATTERN)
    source: str | None = Field(default=None, min_length=2, max_length=120)
    destination: str | None = Field(default=None, min_length=2, max_length=120)
    departure_time: time | None = None
    arrival_time: time | None = None
    days_of_week: list[int] | None = None
    stops: list[Stop] | None = None
    total_seats: int | None = Field(default=None, ge=1, le=2000)
    fare_cents: int | None = Field(default=None, ge=0, le=100_000_000)
    currency: str | None = Field(default=None, max_length=3)
    is_active: bool | None = None

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("At least one operating day is required.")
        if any(day < 1 or day > 7 for day in v):
            raise ValueError("Days must be between 1 (Monday) and 7 (Sunday).")
        return sorted(set(v))


class TrainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    name: str
    train_type: str
    source: str
    destination: str
    departure_time: time | None
    arrival_time: time | None
    days_of_week: list[int]
    stops: list[dict]
    total_seats: int
    fare_cents: int
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AvailabilityDay(BaseModel):
    date: date
    runs: bool
    seats_left: int


class AvailabilityOut(BaseModel):
    train_id: uuid.UUID
    total_seats: int
    days: list[AvailabilityDay]


class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list[dict]
