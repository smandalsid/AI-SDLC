from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking


class BookingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def booked_seat_numbers(self, bus_id: int) -> set[int]:
        statement = select(Booking.seat_number).where(Booking.bus_id == bus_id)
        return set(self.session.scalars(statement))

    def add_many(
        self, bus_id: int, user_id: int, seat_numbers: Sequence[int], booked_at: datetime
    ) -> Sequence[Booking]:
        """Insert one row per seat in the caller's transaction; the caller commits."""
        bookings = [
            Booking(bus_id=bus_id, user_id=user_id, seat_number=seat, booked_at=booked_at)
            for seat in seat_numbers
        ]
        self.session.add_all(bookings)
        self.session.flush()
        return bookings
