from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(self, page: int, page_size: int) -> Sequence[User]:
        statement = select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
        return self.session.scalars(statement).all()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(User)) or 0

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        # The collation may match case-insensitively; the service requires an exact match.
        return self.session.scalars(select(User).where(User.username == username)).first()
