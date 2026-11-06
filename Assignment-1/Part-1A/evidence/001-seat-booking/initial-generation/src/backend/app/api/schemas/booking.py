from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.schemas.common import MAX_ID

MAX_SEATS_PER_REQUEST = 6

Identifier = Annotated[int, Field(strict=True, ge=1, le=MAX_ID)]


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bus_id: Identifier
    user_id: Identifier
    seat_numbers: Annotated[list[Identifier], Field(min_length=1, max_length=MAX_SEATS_PER_REQUEST)]

    @field_validator("seat_numbers")
    @classmethod
    def reject_duplicates(cls, seats: list[int]) -> list[int]:
        if len(set(seats)) != len(seats):
            raise ValueError("seat numbers must not repeat")
        return seats


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bus_id: int
    user_id: int
    seat_number: int
    booked_at: datetime


class BookingResult(BaseModel):
    bookings: list[BookingOut]
