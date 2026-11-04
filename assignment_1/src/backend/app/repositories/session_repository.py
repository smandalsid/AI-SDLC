from datetime import datetime

from sqlalchemy.orm import Session

from app.models.session import UserSession


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self, session_id: str, user_id: int, started_at: datetime, expires_at: datetime
    ) -> None:
        self.session.add(
            UserSession(
                id=session_id, user_id=user_id, started_at=started_at, expires_at=expires_at
            )
        )
        self.session.flush()
