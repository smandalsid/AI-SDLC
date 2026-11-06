from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.sign_in_attempt import SignInAttempt
from app.repositories.protocols import FailureWindow


def failures_statement(username: str, since: datetime) -> Select[tuple[int, datetime]]:
    """Failures newer than `since` and than the username's latest success."""
    latest_success = (
        select(func.max(SignInAttempt.attempted_at))
        .where(SignInAttempt.username == username, SignInAttempt.outcome == "success")
        .scalar_subquery()
    )
    return select(func.count(), func.max(SignInAttempt.attempted_at)).where(
        SignInAttempt.username == username,
        SignInAttempt.outcome == "failure",
        SignInAttempt.attempted_at > since,
        or_(latest_success.is_(None), SignInAttempt.attempted_at > latest_success),
    )


class SignInAttemptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, username: str, outcome: str, at: datetime) -> None:
        self.session.add(SignInAttempt(username=username, outcome=outcome, attempted_at=at))
        self.session.flush()

    def failures_since(self, username: str, since: datetime) -> FailureWindow:
        count, latest_at = self.session.execute(failures_statement(username, since)).one()
        return FailureWindow(count=int(count), latest_at=latest_at)
