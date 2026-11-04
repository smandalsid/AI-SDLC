from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bus import Bus


class BusRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(self, page: int, page_size: int) -> Sequence[Bus]:
        statement = select(Bus).order_by(Bus.id).offset((page - 1) * page_size).limit(page_size)
        return self.session.scalars(statement).all()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(Bus)) or 0

    def get(self, bus_id: int) -> Bus | None:
        return self.session.get(Bus, bus_id)
