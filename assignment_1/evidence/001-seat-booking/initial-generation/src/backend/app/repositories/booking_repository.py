from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errors import SeatAlreadyBookedError
from app.models.booking import Booking

UNIQUE_VIOLATION_CODES = {2601, 2627}
SEAT_CONSTRAINT = "UQ_bookings_bus_seat"


def is_seat_conflict(error: DBAPIError) -> bool:
    # Multi-row inserts raise this error as OperationalError, so match on code and name.
    args = error.orig.args if error.orig is not None else ()
    return bool(args) and args[0] in UNIQUE_VIOLATION_CODES and SEAT_CONSTRAINT in str(error.orig)


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
        try:
            self.session.flush()
        except DBAPIError as error:
            self.session.rollback()
            if is_seat_conflict(error):
                raise SeatAlreadyBookedError from None
            raise
        return bookings
