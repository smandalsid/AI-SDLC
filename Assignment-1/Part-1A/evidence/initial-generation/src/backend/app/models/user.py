from sqlalchemy import CheckConstraint, Identity, Integer, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("LEN(LTRIM(RTRIM(name))) > 0", name="name_not_blank"),
        CheckConstraint("LEN(LTRIM(RTRIM(username))) > 0", name="username_not_blank"),
        CheckConstraint("LEN(password_hash) > 0", name="password_hash_not_blank"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(start=1, increment=1), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(100), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(Unicode(50), nullable=False, unique=True)
    # Argon2id string; never returned by any API.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
