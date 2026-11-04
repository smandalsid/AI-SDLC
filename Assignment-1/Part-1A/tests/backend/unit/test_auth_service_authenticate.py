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
    def now(self) -> datetime:
        return NOW


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


def service_with(*records: SessionRecord) -> AuthService:
    return AuthService(
        users=NoUsers(),
        sessions=StoredSessions({record.session_id: record for record in records}),
        attempts=NoAttempts(),
        verifier=Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),
        codec=CODEC,
        clock=FixedClock(),
        policy=POLICY,
    )


def record(user_id: int = 1, name: str = "Asha") -> SessionRecord:
    return SessionRecord(
        session_id=SESSION_ID,
        user_id=user_id,
        user_name=name,
        started_at=NOW,
        expires_at=EXPIRES,
        ended_at=None,
    )


def token_for(session_id: str = SESSION_ID, user_id: int = 1) -> str:
    return CODEC.encode(TokenClaims(session_id, user_id, EXPIRES), NOW)


def test_a_valid_token_with_its_session_and_user_gives_the_principal() -> None:
    principal = service_with(record()).authenticate(token_for())

    assert principal == Principal(user_id=1, name="Asha", session_id=SESSION_ID)


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
    }

    assert messages == {"Authentication required."}
