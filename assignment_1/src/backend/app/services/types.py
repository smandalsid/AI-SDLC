from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SeatStatus = Literal["available", "booked"]


@dataclass(frozen=True)
class PageResult[T]:
    items: list[T]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True)
class BusSummary:
    id: int
    name: str
    total_seats: int


@dataclass(frozen=True)
class UserSummary:
    id: int
    name: str


@dataclass(frozen=True)
class SeatView:
    seat_number: int
    status: SeatStatus


@dataclass(frozen=True)
class BookingView:
    id: int
    bus_id: int
    user_id: int
    seat_number: int
    booked_at: datetime


@dataclass(frozen=True)
class BusDetailView:
    id: int
    name: str
    total_seats: int
    seats: list[SeatView]
