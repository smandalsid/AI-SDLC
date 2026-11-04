from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import AuthPolicy
from app.core.errors import InvalidCredentialsError
from app.core.passwords import Argon2Hasher
from app.core.tokens import JwtTokenCodec
from app.db.seed import USERS
from app.models.user import User
from app.repositories.protocols import FailureWindow, SessionRecord
from app.services.auth_service import AuthService
from app.services.types import LoginRejected, LoginSuccess, Principal
from pydantic import SecretStr

NOW = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
POLICY = AuthPolicy(
    session_lifetime=timedelta(minutes=30),
    max_failures=5,
    failure_window=timedelta(minutes=5),
    lockout=timedelta(seconds=60),
)
CODEC = JwtTokenCodec(SecretStr("unit-test-signing-" + "k" * 24))
SEEDED = {str(row["username"]) for row in USERS}


class FixedClock:
    def now(self) -> datetime:
        return NOW


class CaseInsensitiveUsers:
    """Like the SQL Server collation: case and trailing spaces do not matter to the store."""

    def __init__(self, users: list[User]) -> None:
        self.by_key = {user.username.lower(): user for user in users}

    def get_by_username(self, username: str) -> User | None:
        return self.by_key.get(username.rstrip().lower())


@dataclass(frozen=True)
class StoredSession:
    session_id: str
    user_id: int
    started_at: datetime
    expires_at: datetime


@dataclass
class RecordingSessions:
    added: list[StoredSession] = field(default_factory=list)
    ended: list[tuple[str, datetime]] = field(default_factory=list)

    def add(
        self, session_id: str, user_id: int, started_at: datetime, expires_at: datetime
    ) -> None:
        self.added.append(StoredSession(session_id, user_id, started_at, expires_at))

    def get_with_user(self, session_id: str) -> SessionRecord | None:
        return None

    def end(self, session_id: str, ended_at: datetime) -> None:
        self.ended.append((session_id, ended_at))


@dataclass
class RecordingAttempts:
    rows: list[tuple[str, str, datetime]] = field(default_factory=list)

    def record(self, username: str, outcome: str, at: datetime) -> None:
        self.rows.append((username, outcome, at))

    def failures_since(self, username: str, since: datetime) -> FailureWindow:
        return FailureWindow(count=0, latest_at=None)


class SpyVerifier:
    def __init__(self, hasher: Argon2Hasher) -> None:
        self.hasher = hasher
        self.verify_calls = 0
        self.dummy_calls = 0

    def verify(self, stored_hash: str, password: str) -> bool:
        self.verify_calls += 1
        return self.hasher.verify(stored_hash, password)

    def verify_dummy(self, password: str) -> bool:
        self.dummy_calls += 1
        return self.hasher.verify_dummy(password)


@dataclass
class Rig:
    service: AuthService
    sessions: RecordingSessions
    attempts: RecordingAttempts
    verifier: SpyVerifier


def make_rig(hashes: Mapping[str, str], hasher: Argon2Hasher, locked: bool = False) -> Rig:
    users = [
        User(
            id=int(str(row["id"])),
            name=str(row["name"]),
            username=str(row["username"]),
            password_hash="!" if locked else hashes[str(row["username"])],
        )
        for row in USERS
    ]
    sessions, attempts, verifier = RecordingSessions(), RecordingAttempts(), SpyVerifier(hasher)
    service = AuthService(
        users=CaseInsensitiveUsers(users),
        sessions=sessions,
        attempts=attempts,
        verifier=verifier,
        codec=CODEC,
        clock=FixedClock(),
        policy=POLICY,
    )
    return Rig(service, sessions, attempts, verifier)


@pytest.fixture
def rig(password_hashes: Mapping[str, str], password_hasher: Argon2Hasher) -> Rig:
    return make_rig(password_hashes, password_hasher)


def test_a_matching_pair_starts_a_session_that_lasts_thirty_minutes(
    rig: Rig, credentials: Mapping[str, str]
) -> None:
    result = rig.service.login("asha", credentials["asha"])

    assert isinstance(result, LoginSuccess)
    assert result.expires_at == NOW + timedelta(minutes=30)
    assert (result.user_id, result.name) == (1, "Asha")
    [stored] = rig.sessions.added
    assert (stored.user_id, stored.started_at, stored.expires_at) == (1, NOW, result.expires_at)
    assert len(stored.session_id) == 32
    int(stored.session_id, 16)
    claims = CODEC.decode(result.access_token)
    assert (claims.session_id, claims.user_id, claims.expires_at) == (
        stored.session_id,
        1,
        result.expires_at,
    )


def test_a_success_records_one_success_attempt_with_the_username_as_typed(
    rig: Rig, credentials: Mapping[str, str]
) -> None:
    rig.service.login("asha", credentials["asha"])

    assert rig.attempts.rows == [("asha", "success", NOW)]


# (username as typed, whose password is sent; None = a wrong password)
REJECTED = [
    pytest.param("asha", None, id="wrong-password"),
    pytest.param("nobody", "asha", id="unknown-username"),
    pytest.param("ravi", "asha", id="other-users-password"),
    pytest.param("ASHA", "asha", id="upper-case-username"),
    pytest.param(" asha", "asha", id="leading-space"),
    pytest.param("asha ", "asha", id="trailing-space"),
]


def password_for(owner: str | None, credentials: Mapping[str, str]) -> str:
    return "not-the-password" if owner is None else credentials[owner]


@pytest.mark.parametrize(("username", "owner"), REJECTED)
def test_every_other_attempt_is_rejected_with_the_generic_error_and_no_session(
    rig: Rig, credentials: Mapping[str, str], username: str, owner: str | None
) -> None:
    result = rig.service.login(username, password_for(owner, credentials))

    assert isinstance(result, LoginRejected)
    assert isinstance(result.error, InvalidCredentialsError)
    assert result.error.message == "Invalid username or password."
    assert rig.attempts.rows == [(username, "failure", NOW)]
    assert rig.sessions.added == []


@pytest.mark.parametrize(("username", "owner"), REJECTED)
def test_exactly_one_hash_verification_happens_on_every_path(
    rig: Rig, credentials: Mapping[str, str], username: str, owner: str | None
) -> None:
    rig.service.login(username, password_for(owner, credentials))

    exact_match = username in SEEDED
    assert (rig.verifier.verify_calls, rig.verifier.dummy_calls) == (
        (1, 0) if exact_match else (0, 1)
    )


def test_the_failure_is_identical_for_every_cause(rig: Rig, credentials: Mapping[str, str]) -> None:
    outcomes = set()
    for username, owner in [("asha", None), ("nobody", "asha"), ("ASHA", "asha"), ("ravi", "asha")]:
        result = rig.service.login(username, password_for(owner, credentials))
        assert isinstance(result, LoginRejected)
        outcomes.add((type(result.error), result.error.code, result.error.message))

    assert outcomes == {
        (InvalidCredentialsError, "invalid_credentials", "Invalid username or password.")
    }


def test_a_locked_account_hash_can_never_sign_in(
    password_hashes: Mapping[str, str],
    password_hasher: Argon2Hasher,
    credentials: Mapping[str, str],
) -> None:
    locked = make_rig(password_hashes, password_hasher, locked=True)

    for password in (credentials["asha"], "!", ""):
        assert isinstance(locked.service.login("asha", password), LoginRejected)
    assert locked.sessions.added == []


def test_logout_ends_only_the_principals_session_and_records_one_signout_attempt(
    rig: Rig,
) -> None:
    principal = Principal(user_id=1, name="Asha", session_id="c" * 32, username="asha")

    rig.service.logout(principal)

    assert rig.sessions.ended == [("c" * 32, NOW)]
    assert rig.attempts.rows == [("asha", "signout", NOW)]
    assert rig.sessions.added == []
