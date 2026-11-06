"""Bounded retry for service failures and the shared live-request budget (FR-14)."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from evaluators.common import Observation

RETRY_DELAYS: tuple[float, ...] = (2.0, 6.0)


class RequestBudget:
    """Thread-safe counter that never hands out more than the cap."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._used = 0
        self._exhausted = False
        self._lock = threading.Lock()

    def try_take(self) -> bool:
        with self._lock:
            if self._used >= self._limit:
                self._exhausted = True
                return False
            self._used += 1
            return True

    @property
    def used(self) -> int:
        return self._used

    @property
    def exhausted(self) -> bool:
        return self._exhausted


@dataclass(frozen=True)
class RetryResult:
    observation: Observation | None
    attempts: int
    not_run: bool


def call_with_retry(
    call: Callable[[], Observation],
    *,
    budget: RequestBudget,
    takes_budget: bool,
    max_retries: int,
    delays: Sequence[float],
    sleep: Callable[[float], None],
) -> RetryResult:
    """Run `call`, retrying infrastructure failures; every attempt costs one request."""
    retries = min(max_retries, len(delays))
    attempts = 0
    for attempt in range(retries + 1):
        if takes_budget and not budget.try_take():
            return RetryResult(None, attempts, True)
        attempts += 1
        observation = call()
        if observation.infra_kind is None or attempt == retries:
            return RetryResult(observation, attempts, False)
        sleep(delays[attempt])
    return RetryResult(None, attempts, True)
