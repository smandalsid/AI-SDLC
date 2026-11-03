from collections.abc import Sequence
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
    def list_page(self, page: int, page_size: int) -> Sequence[User]: ...

    def count(self) -> int: ...

    def get(self, user_id: int) -> User | None: ...
