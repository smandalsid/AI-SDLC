from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

import jwt
from pydantic import SecretStr

from app.core.config import get_settings

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["sid", "sub", "iat", "exp"]


class InvalidTokenError(Exception):
    """The token is not a correctly signed token of this application."""


@dataclass(frozen=True)
class TokenClaims:
    session_id: str
    user_id: int
    expires_at: datetime


class TokenCodec(Protocol):
    def encode(self, claims: TokenClaims, issued_at: datetime) -> str: ...

    def decode(self, token: str) -> TokenClaims: ...


class JwtTokenCodec:
    """Signs and verifies session tokens; expiry is judged by the service with its own clock."""

    def __init__(self, secret: SecretStr) -> None:
        self._secret = secret

    def encode(self, claims: TokenClaims, issued_at: datetime) -> str:
        payload = {
            "sid": claims.session_id,
            "sub": str(claims.user_id),
            "iat": int(issued_at.timestamp()),
            "exp": int(claims.expires_at.timestamp()),
        }
        return jwt.encode(payload, self._secret.get_secret_value(), algorithm=ALGORITHM)

    def decode(self, token: str) -> TokenClaims:
        try:
            raw: dict[str, object] = jwt.decode(
                token,
                self._secret.get_secret_value(),
                algorithms=[ALGORITHM],
                options={"require": REQUIRED_CLAIMS, "verify_exp": False, "verify_iat": False},
            )
            return _to_claims(raw)
        except (jwt.PyJWTError, ValueError, TypeError) as error:
            raise InvalidTokenError("invalid token") from error


def _to_claims(raw: dict[str, object]) -> TokenClaims:
    session_id, subject, expiry = raw["sid"], raw["sub"], raw["exp"]
    if not isinstance(session_id, str) or not isinstance(subject, str):
        raise TypeError("sid and sub must be text")
    if isinstance(expiry, bool) or not isinstance(expiry, int | float):
        raise TypeError("exp must be a number")
    return TokenClaims(session_id, int(subject), datetime.fromtimestamp(expiry, UTC))


@lru_cache
def get_token_codec() -> JwtTokenCodec:
    return JwtTokenCodec(get_settings().jwt_secret)
