from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking


class BookingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def booked_seat_numbers(self, bus_id: int) -> set[int]:
        statement = select(Booking.seat_number).where(Booking.bus_id == bus_id)
        return set(self.session.scalars(statement))
