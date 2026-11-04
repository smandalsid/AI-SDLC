from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import AuthPolicy
from app.core.errors import InvalidCredentialsError, TooManyAttemptsError
from app.core.passwords import Argon2Hasher
from app.core.tokens import JwtTokenCodec
from app.db.seed import USERS
from app.models.user import User
from app.repositories.protocols import FailureWindow, SessionRecord
from app.services.auth_service import AuthService
from app.services.types import LoginRejected, LoginSuccess
from pydantic import SecretStr

START = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
POLICY = AuthPolicy(
    session_lifetime=timedelta(minutes=30),
    max_failures=5,
    failure_window=timedelta(minutes=5),
    lockout=timedelta(seconds=60),
)
CODEC = JwtTokenCodec(SecretStr("unit-test-signing-" + "k" * 24))
WRONG = "not-the-password"


class MovableClock:
    def __init__(self) -> None:
        self.current = START

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


@dataclass
class Users:
    by_name: dict[str, User]
    lookups: int = 0

    def get_by_username(self, username: str) -> User | None:
        self.lookups += 1
        return self.by_name.get(username)


@dataclass
class Sessions:
    added: list[str] = field(default_factory=list)

    def add(
        self, session_id: str, user_id: int, started_at: datetime, expires_at: datetime
    ) -> None:
        self.added.append(session_id)

    def get_with_user(self, session_id: str) -> SessionRecord | None:
        return None

    def end(self, session_id: str, ended_at: datetime) -> None:
        return None


@dataclass
class Attempts:
    rows: list[tuple[str, str, datetime]] = field(default_factory=list)

    def record(self, username: str, outcome: str, at: datetime) -> None:
        self.rows.append((username, outcome, at))

    def failures_since(self, username: str, since: datetime) -> FailureWindow:
        mine = [row for row in self.rows if row[0] == username]
        successes = [at for _, outcome, at in mine if outcome == "success"]
        floor = max([since, *successes])
        failures = [at for _, outcome, at in mine if outcome == "failure" and at > floor]
        return FailureWindow(count=len(failures), latest_at=max(failures, default=None))

    def outcomes(self) -> list[str]:
        return [outcome for _, outcome, _ in self.rows]


@dataclass
class Rig:
    service: AuthService
    clock: MovableClock
    users: Users
    sessions: Sessions
    attempts: Attempts
    credentials: Mapping[str, str]

    def attempt(self, username: str, right: bool = False) -> LoginSuccess | LoginRejected:
        password = self.credentials.get(username, WRONG) if right else WRONG
        return self.service.login(username, password)

    def fail(self, username: str, times: int, gap_seconds: float = 0) -> None:
        for _ in range(times):
            result = self.attempt(username)
            assert isinstance(result, LoginRejected)
            assert isinstance(result.error, InvalidCredentialsError)
            self.clock.advance(seconds=gap_seconds)


@pytest.fixture
def rig(
    password_hashes: Mapping[str, str],
    password_hasher: Argon2Hasher,
    credentials: Mapping[str, str],
) -> Rig:
    users = Users(
        {
            str(row["username"]): User(
                id=int(str(row["id"])),
                name=str(row["name"]),
                username=str(row["username"]),
                password_hash=password_hashes[str(row["username"])],
            )
            for row in USERS
        }
    )
    clock, sessions, attempts = MovableClock(), Sessions(), Attempts()
    service = AuthService(users, sessions, attempts, password_hasher, CODEC, clock, POLICY)
    return Rig(service, clock, users, sessions, attempts, credentials)


def throttled(result: LoginSuccess | LoginRejected) -> TooManyAttemptsError:
    assert isinstance(result, LoginRejected)
    assert isinstance(result.error, TooManyAttemptsError)
    return result.error


def test_four_failures_then_the_right_password_succeeds_and_resets_the_count(rig: Rig) -> None:
    rig.fail("asha", 4)

    assert isinstance(rig.attempt("asha", right=True), LoginSuccess)

    rig.fail("asha", 4)
    assert isinstance(rig.attempt("asha", right=True), LoginSuccess)


@pytest.mark.parametrize("right", [True, False], ids=["right-password", "wrong-password"])
def test_five_failures_block_the_sixth_attempt_whatever_the_password(rig: Rig, right: bool) -> None:
    rig.fail("asha", 5)
    sessions_before = list(rig.sessions.added)

    error = throttled(rig.attempt("asha", right=right))

    assert error.retry_after_seconds == 60
    assert error.message == "Too many failed sign-in attempts. Try again in 60 seconds."
    assert rig.attempts.rows[-1] == ("asha", "throttled", START)
    assert rig.sessions.added == sessions_before


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [(0, 60), (12.4, 48), (30, 30), (59, 1), (59.001, 1)],
)
def test_the_wait_is_the_time_left_rounded_up(rig: Rig, elapsed: float, expected: int) -> None:
    rig.fail("asha", 5)
    rig.clock.advance(seconds=elapsed)

    assert throttled(rig.attempt("asha")).retry_after_seconds == expected


def test_throttled_rows_do_not_count_and_do_not_extend_the_wait(rig: Rig) -> None:
    rig.fail("asha", 5)
    for _ in range(3):
        rig.clock.advance(seconds=10)
        throttled(rig.attempt("asha"))

    rig.clock.advance(seconds=30)

    assert rig.attempts.outcomes().count("failure") == 5
    assert isinstance(rig.attempt("asha", right=True), LoginSuccess)


def test_at_exactly_60_seconds_the_right_password_succeeds(rig: Rig) -> None:
    rig.fail("asha", 5)
    rig.clock.advance(seconds=60)

    assert isinstance(rig.attempt("asha", right=True), LoginSuccess)


def test_at_exactly_60_seconds_a_wrong_password_fails_and_blocks_again(rig: Rig) -> None:
    rig.fail("asha", 5)
    rig.clock.advance(seconds=60)

    result = rig.attempt("asha")
    assert isinstance(result, LoginRejected)
    assert isinstance(result.error, InvalidCredentialsError)

    assert throttled(rig.attempt("asha", right=True)).retry_after_seconds == 60


def test_failures_older_than_five_minutes_do_not_count(rig: Rig) -> None:
    rig.fail("asha", 4)
    rig.clock.advance(minutes=5, seconds=1)
    rig.fail("asha", 1)

    assert isinstance(rig.attempt("asha", right=True), LoginSuccess)


def test_another_username_is_not_affected(rig: Rig) -> None:
    rig.fail("asha", 5)

    assert isinstance(rig.attempt("ravi", right=True), LoginSuccess)


def test_an_unknown_username_is_throttled_exactly_like_a_real_one(rig: Rig) -> None:
    rig.fail("nobody", 5)
    rig.fail("asha", 5)

    unknown = throttled(rig.attempt("nobody"))
    known = throttled(rig.attempt("asha", right=True))

    assert (unknown.code, unknown.message, unknown.retry_after_seconds) == (
        known.code,
        known.message,
        known.retry_after_seconds,
    )


def test_the_throttle_answers_before_any_user_lookup(rig: Rig) -> None:
    rig.fail("asha", 5)
    lookups = rig.users.lookups

    throttled(rig.attempt("asha", right=True))

    assert rig.users.lookups == lookups


def test_the_numbers_come_from_the_policy(
    password_hashes: Mapping[str, str],
    password_hasher: Argon2Hasher,
    credentials: Mapping[str, str],
) -> None:
    strict = AuthPolicy(
        session_lifetime=timedelta(minutes=30),
        max_failures=2,
        failure_window=timedelta(minutes=5),
        lockout=timedelta(seconds=10),
    )
    clock, attempts = MovableClock(), Attempts()
    users = Users(
        {"asha": User(id=1, name="Asha", username="asha", password_hash=password_hashes["asha"])}
    )
    service = AuthService(users, Sessions(), attempts, password_hasher, CODEC, clock, strict)
    for _ in range(2):
        service.login("asha", WRONG)

    result = service.login("asha", credentials["asha"])

    assert isinstance(result, LoginRejected)
    assert isinstance(result.error, TooManyAttemptsError)
    assert result.error.retry_after_seconds == 10
