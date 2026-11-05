"""Layer 2: targets, applied results, input handling, consistency, and the aggregator."""

import pytest

from evaluators.common import JSON, Observation
from evaluators.properties import run_property_checks
from evaluators.properties_other import check_fr5, check_fr6, check_fr7, check_fr8, check_fr9
from harness_helpers import (
    make_action,
    make_applied,
    make_case,
    make_obs,
    make_reminder,
    passed_map,
)

pytestmark = pytest.mark.covers("FR-5", "FR-6", "FR-7", "FR-8", "FR-9", "FR-11")

R1, R2 = make_reminder("r1"), make_reminder("r2", "Gym", "2026-11-07T07:00:00+00:00")


def _cancel(target: str) -> JSON:
    return make_action(intent="cancel", title=None, datetime_iso=None, target_reminder_id=target)


def test_fr5_target_must_equal_the_expected_target() -> None:
    case = make_case(reminders=[R1, R2], expected={"target_reminder_id": "r1"}, traces=("FR-5",))
    assert passed_map(check_fr5(case, make_obs(_cancel("r1"))))["fr5.target"] is True
    assert passed_map(check_fr5(case, make_obs(_cancel("r2"))))["fr5.target"] is False


def test_fr5_zero_or_many_matches_leave_the_target_null() -> None:
    case = make_case(reminders=[R1, R2], expected={"target_reminder_id": None}, traces=("FR-5",))
    clarify = make_action(
        intent="clarify", title=None, datetime_iso=None, clarification_question="Which?"
    )
    assert passed_map(check_fr5(case, make_obs(clarify)))["fr5.target"] is True
    assert passed_map(check_fr5(case, make_obs(_cancel("r1"))))["fr5.target"] is False


def test_fr5_a_target_outside_the_supplied_list_fails() -> None:
    case = make_case(reminders=[R1], expected={"target_reminder_id": "zz"}, traces=("FR-5",))
    assert passed_map(check_fr5(case, make_obs(_cancel("zz"))))["fr5.in_list"] is False


def test_fr6_applied_time_matches_as_an_instant() -> None:
    expected = {"applied_time": "2026-11-05T13:00:00+00:00", "snooze_minutes": 120}
    case = make_case(expected=expected, traces=("AC-20", "FR-6"))
    action = make_action(
        intent="snooze", title=None, datetime_iso=None, target_reminder_id="r3", snooze_minutes=120
    )
    same = make_obs(action, applied=make_applied("snoozed", "r3", "2026-11-05T18:30:00+05:30"))
    other = make_obs(action, applied=make_applied("snoozed", "r3", "2026-11-05T14:00:00+00:00"))
    assert passed_map(check_fr6(case, same)) == {"fr6.new_time": True, "fr6.minutes": True}
    assert passed_map(check_fr6(case, other))["fr6.new_time"] is False
    assert passed_map(check_fr6(case, make_obs(action)))["fr6.new_time"] is False


def test_fr7_removes_exactly_the_target_and_keeps_the_others() -> None:
    expected = {"applied_operation": "cancelled", "unchanged_reminder_ids": ["r1"]}
    case = make_case(reminders=[R1, R2], expected=expected, traces=("AC-22", "FR-7"))
    good = make_obs(_cancel("r2"), applied=make_applied("cancelled", "r2", None, [R1]))
    bad = make_obs(_cancel("r2"), applied=make_applied("cancelled", "r2", None, []))
    assert set(passed_map(check_fr7(case, good)).values()) == {True}
    result = passed_map(check_fr7(case, bad))
    assert result["fr7.removed_exactly_target"] is False and result["fr7.unchanged.r1"] is False


def test_fr8_blank_input_is_rejected_before_the_model() -> None:
    case = make_case(text="", expected={"http_status": 422}, traces=("AC-15", "FR-8"))
    good = make_obs(None, status=422, model_calls=0)
    called = make_obs(None, status=422, model_calls=1)
    assert set(passed_map(check_fr8(case, good)).values()) == {True}
    assert passed_map(check_fr8(case, called))["fr8.no_model_call"] is False


def test_fr8_over_length_input_is_refused_as_too_long_without_the_model() -> None:
    case = make_case(text="x" * 1001, traces=("AC-14", "FR-8"))
    refuse = make_action(intent="refuse", title=None, datetime_iso=None, refusal_reason="too_long")
    assert set(passed_map(check_fr8(case, make_obs(refuse, model_calls=0))).values()) == {True}
    assert (
        passed_map(check_fr8(case, make_obs(refuse, model_calls=1)))["fr8.no_model_call"] is False
    )


def test_fr8_input_of_exactly_1000_characters_is_processed() -> None:
    case = make_case(text="x" * 1000, traces=("AC-16", "FR-8"))
    assert passed_map(check_fr8(case, make_obs(make_action())))["fr8.processed"] is True
    refused = make_action(intent="refuse", title=None, datetime_iso=None, refusal_reason="too_long")
    assert passed_map(check_fr8(case, make_obs(refused)))["fr8.processed"] is False


def _runs(*actions: dict[str, object]) -> list[Observation]:
    return [make_obs(a) for a in actions]


def test_fr9_identical_runs_pass_and_offsets_do_not_matter() -> None:
    case = make_case(consistency=True, traces=("AC-28", "FR-9"))
    same_instant = make_action(datetime_iso="2026-11-09T14:30:00+05:30")
    runs = _runs(make_action(datetime_iso="2026-11-09T09:00:00+00:00"), same_instant, make_action())
    assert passed_map(check_fr9(case, runs, 3)) == {"fr9.run_count": True, "fr9.identical": True}


def test_fr9_a_differing_run_or_missing_runs_fail() -> None:
    case = make_case(consistency=True, traces=("FR-9",))
    different = _runs(
        make_action(), make_action(), make_action(datetime_iso="2026-11-10T09:00:00+00:00")
    )
    assert passed_map(check_fr9(case, different, 3))["fr9.identical"] is False
    assert (
        passed_map(check_fr9(case, _runs(make_action(), make_action()), 3))["fr9.run_count"]
        is False
    )


def test_fr9_applies_only_to_designated_consistency_cases() -> None:
    assert check_fr9(make_case(traces=("FR-9",)), _runs(make_action()), 3) == []


def test_aggregator_checks_the_expected_intent_against_the_case_traces() -> None:
    case = make_case(traces=("AC-1", "FR-1", "INV-3"))
    obs = make_obs(make_action())
    results = run_property_checks(case, obs, [obs], [], 3)
    intent = [r for r in results if r.check_id == "intent"]
    assert len(intent) == 1 and intent[0].passed is True
    assert set(intent[0].requirement_ids) == {"AC-1", "FR-1"}


def test_aggregator_fails_the_intent_check_on_a_mismatch_or_an_http_error() -> None:
    case = make_case()
    wrong = make_obs(
        make_action(intent="cancel", title=None, datetime_iso=None, target_reminder_id="r1")
    )
    assert passed_map(run_property_checks(case, wrong, [wrong], [], 3))["intent"] is False
    broken = make_obs(None, status=502)
    assert passed_map(run_property_checks(case, broken, [broken], [], 3))["intent"] is False


def test_aggregator_includes_consistency_for_designated_cases() -> None:
    case = make_case(consistency=True, traces=("AC-1", "FR-9"))
    obs = make_obs(make_action())
    results = passed_map(run_property_checks(case, obs, [obs, obs, obs], [], 3))
    assert results["fr9.identical"] is True
