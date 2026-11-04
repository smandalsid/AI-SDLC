from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UtcDateTime


class UserSession(Base):
    """One sign-in; valid while ended_at is empty and expires_at has not passed."""

    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("expires_at > started_at", name="expires_after_start"),)

    id: Mapped[str] = mapped_column(CHAR(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
