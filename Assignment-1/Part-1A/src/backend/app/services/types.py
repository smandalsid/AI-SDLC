from dataclasses import dataclass
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
class SeatView:
    seat_number: int
    status: SeatStatus


@dataclass(frozen=True)
class BusDetailView:
    id: int
    name: str
    total_seats: int
    seats: list[SeatView]
