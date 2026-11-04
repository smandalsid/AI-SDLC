from datetime import datetime

from sqlalchemy.orm import Session

from app.models.sign_in_attempt import SignInAttempt


class SignInAttemptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, username: str, outcome: str, at: datetime) -> None:
        self.session.add(SignInAttempt(username=username, outcome=outcome, attempted_at=at))
        self.session.flush()
