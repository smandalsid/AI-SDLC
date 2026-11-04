from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import UserSession
from app.models.user import User
from app.repositories.protocols import SessionRecord


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

    def get_with_user(self, session_id: str) -> SessionRecord | None:
        statement = (
            select(UserSession, User.name)
            .join(User, User.id == UserSession.user_id)
            .where(UserSession.id == session_id)
        )
        row = self.session.execute(statement).first()
        if row is None:
            return None
        stored, user_name = row
        return SessionRecord(
            session_id=stored.id,
            user_id=stored.user_id,
            user_name=user_name,
            started_at=stored.started_at,
            expires_at=stored.expires_at,
            ended_at=stored.ended_at,
        )
