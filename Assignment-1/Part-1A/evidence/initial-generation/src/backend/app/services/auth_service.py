import math
from datetime import datetime
from uuid import uuid4

from app.core.clock import Clock
from app.core.config import AuthPolicy
from app.core.errors import InvalidCredentialsError, TooManyAttemptsError, UnauthenticatedError
from app.core.passwords import PasswordVerifier
from app.core.tokens import InvalidTokenError, TokenClaims, TokenCodec
from app.models.user import User
from app.repositories.protocols import AttemptLog, CredentialReader, SessionStore
from app.services.types import LoginRejected, LoginSuccess, Principal


class AuthService:
    def __init__(
        self,
        users: CredentialReader,
        sessions: SessionStore,
        attempts: AttemptLog,
        verifier: PasswordVerifier,
        codec: TokenCodec,
        clock: Clock,
        policy: AuthPolicy,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.attempts = attempts
        self.verifier = verifier
        self.codec = codec
        self.clock = clock
        self.policy = policy

    def login(self, username: str, password: str) -> LoginSuccess | LoginRejected:
        now = self.clock.now()
        blocked = self._check_throttle(username, now)
        if blocked is not None:
            self.attempts.record(username, "throttled", now)
            return LoginRejected(blocked)
        user = self._authenticated_user(username, password)
        if user is None:
            return self._reject(username, now)
        expires_at = now + self.policy.session_lifetime
        session_id = self._open_session(user.id, now, expires_at)
        self.attempts.record(username, "success", now)
        token = self._issue_token(session_id, user.id, now, expires_at)
        return LoginSuccess(
            access_token=token, expires_at=expires_at, user_id=user.id, name=user.name
        )

    def authenticate(self, token: str) -> Principal:
        """Every refusal raises the same error, so a caller cannot tell why."""
        try:
            claims = self.codec.decode(token)
        except InvalidTokenError:
            raise UnauthenticatedError from None
        record = self.sessions.get_with_user(claims.session_id)
        if record is None or record.user_id != claims.user_id or record.ended_at is not None:
            raise UnauthenticatedError
        # The stored expiry decides, never the token's own claim; use does not extend it.
        if self.clock.now() >= record.expires_at:
            raise UnauthenticatedError
        return Principal(record.user_id, record.user_name, record.session_id, record.username)

    def logout(self, principal: Principal) -> None:
        now = self.clock.now()
        self.sessions.end(principal.session_id, now)
        self.attempts.record(principal.username, "signout", now)

    def _check_throttle(self, username: str, now: datetime) -> TooManyAttemptsError | None:
        """Runs before any user lookup, so a real and an unknown username look the same."""
        window = self.attempts.failures_since(username, now - self.policy.failure_window)
        if window.latest_at is None or window.count < self.policy.max_failures:
            return None
        remaining = window.latest_at + self.policy.lockout - now
        if remaining.total_seconds() <= 0:
            return None
        return TooManyAttemptsError(math.ceil(remaining.total_seconds()))

    def _find_exact_user(self, username: str) -> User | None:
        user = self.users.get_by_username(username)
        # The database collation ignores case and trailing spaces; only an exact match counts.
        return user if user is not None and user.username == username else None

    def _authenticated_user(self, username: str, password: str) -> User | None:
        """One hash verification on every path, so timing does not reveal which part was wrong."""
        user = self._find_exact_user(username)
        if user is None:
            self.verifier.verify_dummy(password)
            return None
        return user if self.verifier.verify(user.password_hash, password) else None

    def _open_session(self, user_id: int, started_at: datetime, expires_at: datetime) -> str:
        session_id = uuid4().hex
        self.sessions.add(session_id, user_id, started_at, expires_at)
        return session_id

    def _issue_token(
        self, session_id: str, user_id: int, issued_at: datetime, expires_at: datetime
    ) -> str:
        return self.codec.encode(TokenClaims(session_id, user_id, expires_at), issued_at)

    def _reject(self, username: str, now: datetime) -> LoginRejected:
        self.attempts.record(username, "failure", now)
        return LoginRejected(InvalidCredentialsError())
