from collections.abc import Sequence

from app.core.clock import Clock
from app.core.errors import BusNotFoundError, InvalidSeatError
from app.repositories.protocols import BookingWriter, BusReader
from app.services.types import BookingView


class BookingService:
    def __init__(self, buses: BusReader, bookings: BookingWriter, clock: Clock) -> None:
        self.buses = buses
        self.bookings = bookings
        self.clock = clock

    def book_seats(
        self, bus_id: int, user_id: int, seat_numbers: Sequence[int]
    ) -> list[BookingView]:
        bus = self.buses.get(bus_id)
        if bus is None:
            raise BusNotFoundError
        if any(seat > bus.total_seats for seat in seat_numbers):
            raise InvalidSeatError
        created = self.bookings.add_many(bus_id, user_id, seat_numbers, self.clock.now())
        return [
            BookingView(
                id=booking.id,
                bus_id=booking.bus_id,
                user_id=booking.user_id,
                seat_number=booking.seat_number,
                booked_at=booking.booked_at,
            )
            for booking in created
        ]
