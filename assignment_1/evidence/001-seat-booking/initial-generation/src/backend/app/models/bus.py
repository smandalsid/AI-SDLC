from sqlalchemy import CheckConstraint, Identity, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Bus(Base):
    __tablename__ = "buses"
    __table_args__ = (
        CheckConstraint("total_seats BETWEEN 1 AND 60", name="total_seats_range"),
        CheckConstraint("LEN(LTRIM(RTRIM(name))) > 0", name="name_not_blank"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(100), nullable=False, unique=True)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
