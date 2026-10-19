import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

CHANNEL_PATTERN = "^(counter|online|phone|agent)$"
GENDER_PATTERN = "^(male|female|other|)$"


class PassengerIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str = Field(default="", pattern=GENDER_PATTERN)
    seat_preference: str = Field(default="", max_length=24)
    id_document: str = Field(default="", max_length=64)


class PassengerOut(PassengerIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class BookingCreate(BaseModel):
    train_id: uuid.UUID
    travel_date: date
    seats: int = Field(ge=1, le=10)
    contact_name: str = Field(min_length=2, max_length=120)
    contact_email: str = Field(default="", max_length=255)
    contact_phone: str = Field(default="", max_length=40)
    passengers: list[PassengerIn] = Field(default_factory=list)
    channel: str = Field(default="counter", pattern=CHANNEL_PATTERN)
    notes: str = Field(default="", max_length=2000)

    @field_validator("passengers")
    @classmethod
    def passenger_count(cls, v: list[PassengerIn]) -> list[PassengerIn]:
        return v


class TrainRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    name: str
    source: str
    destination: str


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pnr: str
    train: TrainRef
    travel_date: date
    contact_name: str
    contact_email: str
    contact_phone: str
    seats: int
    status: str
    total_fare_cents: int
    currency: str
    refund_status: str
    channel: str
    notes: str
    cancelled_at: datetime | None
    created_at: datetime
    passengers: list[PassengerOut]


class BookingListOut(BaseModel):
    id: uuid.UUID
    pnr: str
    train_number: str
    train_name: str
    travel_date: date
    contact_name: str
    seats: int
    status: str
    total_fare_cents: int
    currency: str
    channel: str
    created_at: datetime
