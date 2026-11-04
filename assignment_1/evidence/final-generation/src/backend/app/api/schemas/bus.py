from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.common import Page

MAX_SEATS_PER_BUS = 60


class BusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    total_seats: int = Field(ge=1, le=MAX_SEATS_PER_BUS)


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat_number: int = Field(ge=1)
    status: Literal["available", "booked"]


class BusDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    total_seats: int
    seats: list[SeatOut]


class BusPage(Page[BusOut]):
    pass
