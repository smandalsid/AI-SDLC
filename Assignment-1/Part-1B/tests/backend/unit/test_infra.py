"""Bounded retry and the shared live-request budget (FR-14, MEC-17, MEC-18)."""

from collections.abc import Callable

import pytest

from evaluators.common import Observation
from harness_helpers import make_obs
from infra import RETRY_DELAYS, RequestBudget, call_with_retry

pytestmark = pytest.mark.covers("FR-14", "AC-29", "MEC-18")


def _infra() -> Observation:
    return make_obs(None, status=503, infra_kind="timeout")


def _ok() -> Observation:
    return make_obs({"intent": "clarify"})


def _scripted(items: list[Observation]) -> Callable[[], Observation]:
    queue = list(items)
    return lambda: queue.pop(0)


def test_budget_hands_out_requests_up_to_the_cap() -> None:
    budget = RequestBudget(2)
    assert [budget.try_take(), budget.try_take(), budget.try_take()] == [True, True, False]
    assert budget.used == 2 and budget.exhausted is True


def test_default_delays_are_two_then_six_seconds() -> None:
    assert RETRY_DELAYS == (2.0, 6.0)


def test_infra_error_is_retried_with_backoff_and_every_retry_costs_a_request() -> None:
    budget = RequestBudget(60)
    sleeps: list[float] = []
    result = call_with_retry(
        _scripted([_infra(), _infra(), _ok()]),
        budget=budget,
        takes_budget=True,
        max_retries=2,
        delays=RETRY_DELAYS,
        sleep=sleeps.append,
    )
    assert result.observation is not None and result.observation.infra_kind is None
    assert result.attempts == 3 and sleeps == [2.0, 6.0] and budget.used == 3


def test_infra_error_after_the_retries_is_returned_as_is() -> None:
    result = call_with_retry(
        _scripted([_infra(), _infra(), _infra()]),
        budget=RequestBudget(60),
        takes_budget=True,
        max_retries=2,
        delays=RETRY_DELAYS,
        sleep=lambda s: None,
    )
    assert result.observation is not None and result.observation.infra_kind == "timeout"
    assert result.attempts == 3 and result.not_run is False


def test_a_denied_request_is_not_run() -> None:
    result = call_with_retry(
        _scripted([_infra(), _ok()]),
        budget=RequestBudget(1),
        takes_budget=True,
        max_retries=2,
        delays=RETRY_DELAYS,
        sleep=lambda s: None,
    )
    assert result.not_run is True and result.observation is None


def test_calls_that_never_reach_the_model_do_not_use_the_budget() -> None:
    budget = RequestBudget(0)
    result = call_with_retry(
        _scripted([_ok()]),
        budget=budget,
        takes_budget=False,
        max_retries=2,
        delays=RETRY_DELAYS,
        sleep=lambda s: None,
    )
    assert result.not_run is False and budget.used == 0


def test_a_non_infrastructure_exception_is_never_retried_or_hidden() -> None:
    def boom() -> Observation:
        raise RuntimeError("application bug")

    with pytest.raises(RuntimeError, match="application bug"):
        call_with_retry(
            boom,
            budget=RequestBudget(60),
            takes_budget=True,
            max_retries=2,
            delays=RETRY_DELAYS,
            sleep=lambda s: None,
        )
