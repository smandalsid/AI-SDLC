from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.clock import Clock, SystemClock
from app.db.session import get_session
from app.repositories.booking_repository import BookingRepository
from app.repositories.bus_repository import BusRepository
from app.repositories.user_repository import UserRepository
from app.services.bus_service import BusService
from app.services.user_service import UserService

# scope="function" commits before the response is sent, so a 201 is never returned uncommitted.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]


def get_clock() -> Clock:
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]


def get_bus_service(session: SessionDep) -> BusService:
    return BusService(BusRepository(session), BookingRepository(session))


BusServiceDep = Annotated[BusService, Depends(get_bus_service)]


def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserRepository(session))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
