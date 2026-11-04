from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.core.errors import AppError

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


@dataclass(frozen=True)
class LoginSuccess:
    access_token: str
    expires_at: datetime
    user_id: int
    name: str


@dataclass(frozen=True)
class LoginRejected:
    """A refused sign-in is a value, not an exception, so the attempt row still commits."""

    error: AppError


@dataclass(frozen=True)
class Principal:
    """The authenticated caller of a request."""

    user_id: int
    name: str
    session_id: str
