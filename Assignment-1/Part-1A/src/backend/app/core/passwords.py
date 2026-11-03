from secrets import token_urlsafe
from typing import Protocol

import argon2
from argon2.exceptions import InvalidHashError, VerificationError


class PasswordVerifier(Protocol):
    def verify(self, stored_hash: str, password: str) -> bool: ...

    def verify_dummy(self, password: str) -> bool: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...


class Argon2Hasher:
    """Argon2id hashing; cost parameters are stored in each hash, so old hashes keep verifying."""

    def __init__(
        self,
        time_cost: int | None = None,
        memory_cost: int | None = None,
        parallelism: int | None = None,
    ) -> None:
        self._hasher = argon2.PasswordHasher(
            time_cost=argon2.DEFAULT_TIME_COST if time_cost is None else time_cost,
            memory_cost=argon2.DEFAULT_MEMORY_COST if memory_cost is None else memory_cost,
            parallelism=argon2.DEFAULT_PARALLELISM if parallelism is None else parallelism,
        )
        # Hash of a value no user has: unknown usernames are verified against it so they take
        # as long as known ones.
        self._dummy_hash = self._hasher.hash(token_urlsafe(16))

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, stored_hash: str, password: str) -> bool:
        """False for a wrong password and for any invalid or locked hash (for example `!`)."""
        try:
            return self._hasher.verify(stored_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def verify_dummy(self, password: str) -> bool:
        self.verify(self._dummy_hash, password)
        return False
