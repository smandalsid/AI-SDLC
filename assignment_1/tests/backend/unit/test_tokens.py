from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import jwt
import pytest
from app.core.tokens import InvalidTokenError, JwtTokenCodec, TokenClaims
from pydantic import SecretStr

SIGNING_KEY = "a" * 40
OTHER_KEY = "b" * 40
ISSUED_AT = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
EXPIRES_AT = datetime(2026, 1, 15, 11, 0, tzinfo=UTC)
CLAIMS = TokenClaims(
    session_id="0123456789abcdef0123456789abcdef", user_id=7, expires_at=EXPIRES_AT
)


def payload() -> dict[str, object]:
    return {
        "sid": CLAIMS.session_id,
        "sub": str(CLAIMS.user_id),
        "iat": int(ISSUED_AT.timestamp()),
        "exp": int(EXPIRES_AT.timestamp()),
    }


@pytest.fixture
def codec() -> JwtTokenCodec:
    return JwtTokenCodec(SecretStr(SIGNING_KEY))


def test_encode_then_decode_round_trips_the_claims(codec: JwtTokenCodec) -> None:
    assert codec.decode(codec.encode(CLAIMS, ISSUED_AT)) == CLAIMS


def test_claims_are_a_frozen_dataclass() -> None:
    with pytest.raises(FrozenInstanceError):
        CLAIMS.user_id = 8  # type: ignore[misc]  # proves the dataclass is frozen


def test_the_token_never_contains_the_signing_key(codec: JwtTokenCodec) -> None:
    assert SIGNING_KEY not in codec.encode(CLAIMS, ISSUED_AT)


def test_a_token_whose_expiry_is_in_the_past_still_decodes(codec: JwtTokenCodec) -> None:
    long_ago = TokenClaims(CLAIMS.session_id, CLAIMS.user_id, datetime(2000, 1, 1, tzinfo=UTC))

    assert codec.decode(codec.encode(long_ago, datetime(1999, 12, 31, tzinfo=UTC))) == long_ago


def test_a_token_with_one_character_changed_is_rejected(codec: JwtTokenCodec) -> None:
    header, body, signature = codec.encode(CLAIMS, ISSUED_AT).split(".")
    changed = ("A" if signature[0] != "A" else "B") + signature[1:]

    with pytest.raises(InvalidTokenError):
        codec.decode(f"{header}.{body}.{changed}")


def test_a_token_signed_with_another_key_is_rejected(codec: JwtTokenCodec) -> None:
    foreign = JwtTokenCodec(SecretStr(OTHER_KEY)).encode(CLAIMS, ISSUED_AT)

    with pytest.raises(InvalidTokenError):
        codec.decode(foreign)


def test_a_token_with_alg_none_is_rejected(codec: JwtTokenCodec) -> None:
    unsigned = jwt.encode(payload(), None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        codec.decode(unsigned)


def test_a_token_with_another_algorithm_is_rejected(codec: JwtTokenCodec) -> None:
    other = jwt.encode(payload(), SIGNING_KEY, algorithm="HS512")

    with pytest.raises(InvalidTokenError):
        codec.decode(other)


@pytest.mark.parametrize("missing", ["sid", "sub", "iat", "exp"])
def test_a_token_without_a_required_claim_is_rejected(codec: JwtTokenCodec, missing: str) -> None:
    claims = payload()
    del claims[missing]

    with pytest.raises(InvalidTokenError):
        codec.decode(jwt.encode(claims, SIGNING_KEY, algorithm="HS256"))


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c", "Bearer abc", " "])
def test_garbage_is_rejected(codec: JwtTokenCodec, token: str) -> None:
    with pytest.raises(InvalidTokenError):
        codec.decode(token)


def test_a_non_numeric_subject_is_rejected(codec: JwtTokenCodec) -> None:
    claims = payload()
    claims["sub"] = "not-a-number"

    with pytest.raises(InvalidTokenError):
        codec.decode(jwt.encode(claims, SIGNING_KEY, algorithm="HS256"))
