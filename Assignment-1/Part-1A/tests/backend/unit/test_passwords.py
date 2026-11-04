import argon2
import pytest
from app.core.passwords import Argon2Hasher

SECRET_TEXT = "correct horse battery staple"


@pytest.fixture
def hasher() -> Argon2Hasher:
    return Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1)


@pytest.fixture
def verify_calls(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Counts every call of the underlying argon2 verification."""
    calls: list[int] = []
    original = argon2.PasswordHasher.verify

    def counting_verify(
        self: argon2.PasswordHasher, hash: str | bytes, password: str | bytes
    ) -> bool:
        calls.append(1)
        return original(self, hash, password)

    monkeypatch.setattr(argon2.PasswordHasher, "verify", counting_verify)
    return calls


def test_hash_is_an_argon2id_string_and_salted(hasher: Argon2Hasher) -> None:
    first = hasher.hash(SECRET_TEXT)
    second = hasher.hash(SECRET_TEXT)

    assert first.startswith("$argon2id$")
    assert first != second
    assert SECRET_TEXT not in first


def test_verify_accepts_the_right_password_and_rejects_a_wrong_one(hasher: Argon2Hasher) -> None:
    stored = hasher.hash(SECRET_TEXT)

    assert hasher.verify(stored, SECRET_TEXT) is True
    assert hasher.verify(stored, SECRET_TEXT + "x") is False


@pytest.mark.parametrize(
    "password",
    ["p" * 128, "pässwörd-日本語", " leading and trailing  ", "Mixed Case"],
)
def test_passwords_are_compared_exactly_as_typed(hasher: Argon2Hasher, password: str) -> None:
    stored = hasher.hash(password)

    assert hasher.verify(stored, password) is True
    assert hasher.verify(stored, password.strip() + "!") is False
    if password != password.strip():
        assert hasher.verify(stored, password.strip()) is False
    if password != password.lower():
        assert hasher.verify(stored, password.lower()) is False


def test_a_hash_made_with_other_cost_parameters_still_verifies(hasher: Argon2Hasher) -> None:
    other = Argon2Hasher(time_cost=2, memory_cost=16, parallelism=1)

    assert hasher.verify(other.hash(SECRET_TEXT), SECRET_TEXT) is True


@pytest.mark.parametrize("stored", ["!", "", "not-a-hash", "$argon2id$broken", "x" * 300])
def test_an_invalid_or_locked_hash_never_verifies_and_never_raises(
    hasher: Argon2Hasher, stored: str
) -> None:
    assert hasher.verify(stored, SECRET_TEXT) is False


def test_verify_dummy_performs_one_verification_and_returns_false(
    hasher: Argon2Hasher, verify_calls: list[int]
) -> None:
    assert hasher.verify_dummy(SECRET_TEXT) is False
    assert len(verify_calls) == 1


def test_verify_does_one_verification_for_a_real_hash(
    hasher: Argon2Hasher, verify_calls: list[int]
) -> None:
    stored = hasher.hash(SECRET_TEXT)

    assert hasher.verify(stored, "wrong") is False
    assert len(verify_calls) == 1


def test_no_failure_text_contains_the_password(hasher: Argon2Hasher) -> None:
    password = "pw-that-must-not-leak-9f3"

    assert hasher.verify("!", password) is False
    assert hasher.verify_dummy(password) is False
    assert password not in repr(hasher)
