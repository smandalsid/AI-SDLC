"""Layer 2 entry point: all property and guardrail checks for one case."""

from __future__ import annotations

from evaluators.common import JSON, CheckResult, Observation, action_of, result
from evaluators.properties_guardrails import (
    check_gr1,
    check_gr2,
    check_gr3,
    check_gr4,
    check_gr5,
    check_gr6,
)
from evaluators.properties_other import check_fr5, check_fr6, check_fr7, check_fr8, check_fr9
from evaluators.properties_time import check_fr1, check_fr2, check_fr3, check_fr4


def check_intent(case: JSON, obs: Observation) -> list[CheckResult]:
    """The observed intent equals the expected one; traced to the case's non-INV requirements."""
    want = case["expected"].get("intent")
    if want is None:
        return []
    reqs = tuple(t for t in case["traces"] if not t.startswith("INV-"))
    observed = (action_of(obs) or {}).get("intent")
    shown = observed if observed is not None else f"no action (HTTP {obs.status_code})"
    return [result("property", "intent", reqs, observed == want, want, shown)]


def run_property_checks(
    case: JSON, obs: Observation, runs: list[Observation], sentinels: list[str], consistency_k: int
) -> list[CheckResult]:
    checks: list[CheckResult] = check_intent(case, obs)
    for checker in (
        check_fr1,
        check_fr2,
        check_fr3,
        check_fr4,
        check_fr5,
        check_fr6,
        check_fr7,
        check_fr8,
    ):
        checks += checker(case, obs)
    for gr_checker in (check_gr1, check_gr2, check_gr3, check_gr5, check_gr6):
        checks += gr_checker(case, obs)
    checks += check_gr4(case, obs, sentinels)
    checks += check_fr9(case, runs, consistency_k)
    return checks
