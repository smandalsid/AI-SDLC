from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.api.schemas.common import Page


class BusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    total_seats: int


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat_number: int
    status: Literal["available", "booked"]


class BusDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    total_seats: int
    seats: list[SeatOut]


class BusPage(Page[BusOut]):
    pass
