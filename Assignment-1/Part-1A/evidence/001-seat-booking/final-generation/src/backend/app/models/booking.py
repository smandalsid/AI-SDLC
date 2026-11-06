from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Identity, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UtcDateTime


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # The double-booking guard; its leading column also serves "booked seats for a bus".
        UniqueConstraint("bus_id", "seat_number", name="UQ_bookings_bus_seat"),
        CheckConstraint("seat_number >= 1", name="seat_number_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    booked_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
