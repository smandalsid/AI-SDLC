from collections.abc import Sequence
from typing import Protocol

from app.models.bus import Bus


class BusReader(Protocol):
    def list_page(self, page: int, page_size: int) -> Sequence[Bus]: ...

    def count(self) -> int: ...

    def get(self, bus_id: int) -> Bus | None: ...


class BookedSeatReader(Protocol):
    def booked_seat_numbers(self, bus_id: int) -> set[int]: ...
