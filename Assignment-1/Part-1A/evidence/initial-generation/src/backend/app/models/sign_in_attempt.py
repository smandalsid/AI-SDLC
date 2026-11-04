from datetime import datetime

from sqlalchemy import CheckConstraint, Identity, Index, Integer, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UtcDateTime


class SignInAttempt(Base):
    """Audit trail and failure counter; the username is as typed and never matches a foreign key."""

    __tablename__ = "sign_in_attempts"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success','failure','throttled','signout')", name="outcome_known"
        ),
        Index("ix_sign_in_attempts_username_attempted_at", "username", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    username: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
