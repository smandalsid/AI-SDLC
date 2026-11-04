from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.clock import Clock, SystemClock
from app.core.config import AuthPolicy, get_settings
from app.core.errors import UnauthenticatedError
from app.core.passwords import Argon2Hasher, PasswordVerifier
from app.core.tokens import TokenCodec, get_token_codec
from app.db.session import get_session
from app.repositories.booking_repository import BookingRepository
from app.repositories.bus_repository import BusRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.sign_in_attempt_repository import SignInAttemptRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.booking_service import BookingService
from app.services.bus_service import BusService
from app.services.types import Principal
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


def get_booking_service(session: SessionDep, clock: ClockDep) -> BookingService:
    return BookingService(
        BusRepository(session), UserRepository(session), BookingRepository(session), clock
    )


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]


@lru_cache
def get_password_verifier() -> PasswordVerifier:
    return Argon2Hasher()


def get_auth_policy() -> AuthPolicy:
    return get_settings().auth_policy


def get_auth_service(
    session: SessionDep,
    clock: ClockDep,
    verifier: Annotated[PasswordVerifier, Depends(get_password_verifier)],
    codec: Annotated[TokenCodec, Depends(get_token_codec)],
    policy: Annotated[AuthPolicy, Depends(get_auth_policy)],
) -> AuthService:
    return AuthService(
        UserRepository(session),
        SessionRepository(session),
        SignInAttemptRepository(session),
        verifier,
        codec,
        clock,
        policy,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# auto_error is off so a missing credential gets the shared 401 body instead of FastAPI's own.
bearer_scheme = HTTPBearer(auto_error=False)


def require_session(
    service: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    if credentials is None:
        raise UnauthenticatedError
    return service.authenticate(credentials.credentials)


CurrentUserDep = Annotated[Principal, Depends(require_session)]
