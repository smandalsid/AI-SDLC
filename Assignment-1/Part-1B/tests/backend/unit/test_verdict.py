"""PASS / FAIL / INVALID decision rules (FR-13, FR-14, AC-29, AC-30, AC-32)."""

import pytest

from summarize import VerdictInputs, compute_verdict

pytestmark = pytest.mark.covers("FR-13", "FR-14", "AC-29", "AC-30", "AC-32")


def _inputs(**overrides: object) -> VerdictInputs:
    base: dict[str, object] = {
        "preflight_ok": True,
        "not_run": 0,
        "cap_reached": False,
        "infra_share": 0.0,
        "infra_max_share": 0.10,
        "final_requested": False,
        "mode": "live",
        "failed_gates": (),
        "structural_rate": 1.0,
        "structural_min": 1.0,
        "guardrail_rate": 1.0,
        "guardrail_min": 1.0,
        "aggregate": 0.95,
        "aggregate_min": 0.85,
        "consistency_failures": (),
    }
    return VerdictInputs(**{**base, **overrides})  # type: ignore[arg-type]  # test builder


def test_all_conditions_met_is_pass() -> None:
    assert compute_verdict(_inputs()) == "PASS"


def test_aggregate_exactly_at_threshold_passes_and_just_below_fails() -> None:
    assert compute_verdict(_inputs(aggregate=0.85)) == "PASS"
    assert compute_verdict(_inputs(aggregate=0.849)) == "FAIL"


def test_structural_or_guardrail_below_minimum_fails() -> None:
    assert compute_verdict(_inputs(structural_rate=0.97)) == "FAIL"
    assert compute_verdict(_inputs(guardrail_rate=0.9)) == "FAIL"


def test_infra_share_at_ten_percent_is_not_invalid() -> None:
    assert compute_verdict(_inputs(infra_share=0.10)) == "PASS"


def test_infra_share_above_ten_percent_is_invalid_regardless_of_scores() -> None:
    assert compute_verdict(_inputs(infra_share=4 / 33, aggregate=1.0)) == "INVALID"


@pytest.mark.parametrize(
    "override",
    [{"preflight_ok": False}, {"not_run": 1}, {"cap_reached": True}],
)
def test_preflight_unrun_cases_or_cap_are_invalid(override: dict[str, object]) -> None:
    assert compute_verdict(_inputs(**override)) == "INVALID"


def test_final_result_from_a_non_live_run_is_invalid() -> None:
    assert compute_verdict(_inputs(mode="replay", final_requested=True)) == "INVALID"
    assert compute_verdict(_inputs(mode="replay", final_requested=False)) == "PASS"


def test_a_failed_gate_turns_a_would_be_pass_into_fail() -> None:
    assert compute_verdict(_inputs(failed_gates=("lint",))) == "FAIL"


def test_invalid_wins_over_fail() -> None:
    assert compute_verdict(_inputs(failed_gates=("lint",), infra_share=0.5)) == "INVALID"


def test_a_differing_consistency_case_fails_the_run() -> None:
    assert compute_verdict(_inputs(consistency_failures=("N01",))) == "FAIL"
