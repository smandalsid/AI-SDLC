from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.clock import Clock, SystemClock
from app.db.session import get_session

# scope="function" commits before the response is sent, so a 201 is never returned uncommitted.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]


def get_clock() -> Clock:
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]
