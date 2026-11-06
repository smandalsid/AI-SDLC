import inspect
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from app.core.errors import BusNotFoundError, InvalidSeatError
from app.models.booking import Booking
from app.models.bus import Bus
from app.services.booking_service import BookingService

NOW = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeBuses:
    def get(self, bus_id: int) -> Bus | None:
        return Bus(id=1, name="Bus A", total_seats=20) if bus_id == 1 else None

    def list_page(self, page: int, page_size: int) -> Sequence[Bus]:
        return []

    def count(self) -> int:
        return 0


class RecordingWriter:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, list[int], datetime]] = []

    def add_many(
        self, bus_id: int, user_id: int, seat_numbers: Sequence[int], booked_at: datetime
    ) -> Sequence[Booking]:
        self.calls.append((bus_id, user_id, list(seat_numbers), booked_at))
        return [
            Booking(id=index, bus_id=bus_id, user_id=user_id, seat_number=seat, booked_at=booked_at)
            for index, seat in enumerate(seat_numbers, start=1)
        ]


def make_service(writer: RecordingWriter) -> BookingService:
    return BookingService(FakeBuses(), writer, FakeClock())


def test_books_every_seat_with_one_timestamp_from_the_clock() -> None:
    writer = RecordingWriter()

    result = make_service(writer).book_seats(bus_id=1, user_id=1, seat_numbers=[3, 4])

    assert writer.calls == [(1, 1, [3, 4], NOW)]
    assert [(b.id, b.bus_id, b.user_id, b.seat_number) for b in result] == [
        (1, 1, 1, 3),
        (2, 1, 1, 4),
    ]
    assert {b.booked_at for b in result} == {NOW}


def test_the_last_seat_of_the_bus_is_valid() -> None:
    writer = RecordingWriter()

    make_service(writer).book_seats(bus_id=1, user_id=1, seat_numbers=[20])

    assert len(writer.calls) == 1


def test_a_seat_beyond_the_bus_is_invalid_and_nothing_is_written() -> None:
    writer = RecordingWriter()

    with pytest.raises(InvalidSeatError):
        make_service(writer).book_seats(bus_id=1, user_id=1, seat_numbers=[3, 21])

    assert writer.calls == []


def test_an_unknown_bus_is_reported_and_nothing_is_written() -> None:
    writer = RecordingWriter()

    with pytest.raises(BusNotFoundError):
        make_service(writer).book_seats(bus_id=99, user_id=1, seat_numbers=[3])

    assert writer.calls == []


def test_the_given_user_id_is_stored_without_any_user_lookup() -> None:
    writer = RecordingWriter()

    result = make_service(writer).book_seats(bus_id=1, user_id=2, seat_numbers=[5])

    assert writer.calls == [(1, 2, [5], NOW)]
    assert [b.user_id for b in result] == [2]


def test_the_service_takes_only_buses_bookings_and_the_clock() -> None:
    parameters = list(inspect.signature(BookingService).parameters)

    assert parameters == ["buses", "bookings", "clock"]
