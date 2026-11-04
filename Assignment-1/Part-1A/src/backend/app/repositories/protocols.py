from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.booking import Booking
from app.models.bus import Bus
from app.models.user import User


class BusReader(Protocol):
    def list_page(self, page: int, page_size: int) -> Sequence[Bus]: ...

    def count(self) -> int: ...

    def get(self, bus_id: int) -> Bus | None: ...


class BookedSeatReader(Protocol):
    def booked_seat_numbers(self, bus_id: int) -> set[int]: ...


class BookingWriter(Protocol):
    def add_many(
        self, bus_id: int, user_id: int, seat_numbers: Sequence[int], booked_at: datetime
    ) -> Sequence[Booking]: ...


class UserReader(Protocol):
    def get(self, user_id: int) -> User | None: ...

    def get_by_username(self, username: str) -> User | None: ...


class CredentialReader(Protocol):
    def get_by_username(self, username: str) -> User | None: ...


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    user_id: int
    user_name: str
    started_at: datetime
    expires_at: datetime
    ended_at: datetime | None


class SessionStore(Protocol):
    def add(
        self, session_id: str, user_id: int, started_at: datetime, expires_at: datetime
    ) -> None: ...

    def get_with_user(self, session_id: str) -> SessionRecord | None: ...


class AttemptLog(Protocol):
    def record(self, username: str, outcome: str, at: datetime) -> None: ...
