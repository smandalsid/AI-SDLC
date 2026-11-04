from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import AuthPolicy
from app.core.errors import UnauthenticatedError
from app.core.passwords import Argon2Hasher
from app.core.tokens import JwtTokenCodec, TokenClaims
from app.models.user import User
from app.repositories.protocols import SessionRecord
from app.services.auth_service import AuthService
from app.services.types import Principal
from pydantic import SecretStr

NOW = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
EXPIRES = NOW + timedelta(minutes=30)
SESSION_ID = "a" * 32
POLICY = AuthPolicy(
    session_lifetime=timedelta(minutes=30),
    max_failures=5,
    failure_window=timedelta(minutes=5),
    lockout=timedelta(seconds=60),
)
CODEC = JwtTokenCodec(SecretStr("unit-test-signing-" + "k" * 24))


class FixedClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class NoUsers:
    def get_by_username(self, username: str) -> User | None:
        return None


class NoAttempts:
    def record(self, username: str, outcome: str, at: datetime) -> None:
        return None


@dataclass
class StoredSessions:
    records: dict[str, SessionRecord]

    def add(
        self, session_id: str, user_id: int, started_at: datetime, expires_at: datetime
    ) -> None:
        raise AssertionError("authenticate never writes")

    def get_with_user(self, session_id: str) -> SessionRecord | None:
        return self.records.get(session_id)

    def end(self, session_id: str, ended_at: datetime) -> None:
        raise AssertionError("authenticate never writes")


def service_with(*records: SessionRecord, clock: FixedClock | None = None) -> AuthService:
    return AuthService(
        users=NoUsers(),
        sessions=StoredSessions({record.session_id: record for record in records}),
        attempts=NoAttempts(),
        verifier=Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),
        codec=CODEC,
        clock=clock or FixedClock(),
        policy=POLICY,
    )


def record(user_id: int = 1, name: str = "Asha", ended_at: datetime | None = None) -> SessionRecord:
    return SessionRecord(
        session_id=SESSION_ID,
        user_id=user_id,
        user_name=name,
        username=name.lower(),
        started_at=NOW,
        expires_at=EXPIRES,
        ended_at=ended_at,
    )


def token_for(session_id: str = SESSION_ID, user_id: int = 1) -> str:
    return CODEC.encode(TokenClaims(session_id, user_id, EXPIRES), NOW)


def test_a_valid_token_with_its_session_and_user_gives_the_principal() -> None:
    principal = service_with(record()).authenticate(token_for())

    assert principal == Principal(user_id=1, name="Asha", session_id=SESSION_ID, username="asha")


def refused(service: AuthService, token: str) -> str:
    with pytest.raises(UnauthenticatedError) as caught:
        service.authenticate(token)
    return caught.value.message


def test_every_refusal_raises_the_same_generic_error() -> None:
    messages = {
        refused(service_with(record()), "not-a-token"),
        refused(service_with(record()), token_for(session_id="b" * 32)),
        refused(service_with(), token_for()),
        refused(service_with(record(user_id=2, name="Ravi")), token_for(user_id=1)),
        refused(service_with(record(ended_at=NOW)), token_for()),
    }

    assert messages == {"Authentication required."}


@pytest.mark.parametrize("ended_at", [NOW - timedelta(minutes=1), NOW, NOW + timedelta(minutes=1)])
def test_a_session_with_an_end_time_is_refused_whatever_the_time(ended_at: datetime) -> None:
    assert (
        refused(service_with(record(ended_at=ended_at)), token_for()) == "Authentication required."
    )


def test_a_session_is_accepted_29_minutes_59_seconds_after_sign_in() -> None:
    clock = FixedClock(NOW + timedelta(minutes=29, seconds=59))

    principal = service_with(record(), clock=clock).authenticate(token_for())

    assert principal.user_id == 1


@pytest.mark.parametrize("age", [timedelta(minutes=30), timedelta(minutes=30, seconds=1)])
def test_a_session_is_refused_from_exactly_30_minutes_on(age: timedelta) -> None:
    clock = FixedClock(NOW + age)

    assert refused(service_with(record(), clock=clock), token_for()) == "Authentication required."


def test_use_does_not_extend_the_expiry() -> None:
    clock = FixedClock(NOW + timedelta(minutes=20))
    service = service_with(record(), clock=clock)

    service.authenticate(token_for())
    clock.current = NOW + timedelta(minutes=30)

    assert refused(service, token_for()) == "Authentication required."


def test_the_tokens_own_expiry_claim_does_not_decide() -> None:
    far_future = CODEC.encode(TokenClaims(SESSION_ID, 1, NOW + timedelta(days=365)), NOW)
    long_past = CODEC.encode(TokenClaims(SESSION_ID, 1, NOW - timedelta(days=1)), NOW)
    expired = FixedClock(NOW + timedelta(minutes=45))

    assert refused(service_with(record(), clock=expired), far_future) == "Authentication required."
    assert service_with(record()).authenticate(long_past).user_id == 1
