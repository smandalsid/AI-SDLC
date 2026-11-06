"""Layer 2: time and clarification properties FR-1 to FR-4."""

import pytest

from evaluators.common import JSON
from evaluators.properties_time import check_fr1, check_fr2, check_fr3, check_fr4
from harness_helpers import make_action, make_case, make_obs, passed_map

pytestmark = pytest.mark.covers("FR-1", "FR-2", "FR-3", "FR-4", "FR-11")

NY = {"timezone": "America/New_York", "now": "2027-03-13T12:00:00-05:00"}


def _clarify() -> JSON:
    return make_action(
        intent="clarify", title=None, datetime_iso=None, clarification_question="What time?"
    )


def test_fr1_future_and_local_offset_pass() -> None:
    case = make_case(traces=("AC-1", "FR-1"))
    result = passed_map(check_fr1(case, make_obs(make_action())))
    assert result == {"fr1.future": True, "fr1.offset": True}


def test_fr1_time_equal_to_now_is_not_in_the_future() -> None:
    action = make_action(datetime_iso="2026-11-05T10:00:00+00:00")
    assert passed_map(check_fr1(make_case(), make_obs(action)))["fr1.future"] is False


def test_fr1_offset_must_match_the_zone_at_that_instant() -> None:
    case = make_case(timezone=NY["timezone"], now=NY["now"])
    wrong = make_action(datetime_iso="2027-03-14T09:00:00-05:00")
    right = make_action(datetime_iso="2027-03-14T09:00:00-04:00")
    assert passed_map(check_fr1(case, make_obs(wrong)))["fr1.offset"] is False
    assert passed_map(check_fr1(case, make_obs(right)))["fr1.offset"] is True


def test_fr1_expected_clarify_requires_no_datetime() -> None:
    case = make_case(expected={"intent": "clarify"}, traces=("AC-36", "FR-1"))
    assert passed_map(check_fr1(case, make_obs(_clarify())))["fr1.clarify_null"] is True
    assert passed_map(check_fr1(case, make_obs(make_action())))["fr1.clarify_null"] is False


def test_checks_apply_only_when_the_case_traces_the_requirement() -> None:
    case = make_case(traces=("AC-4", "FR-2"))
    assert check_fr1(case, make_obs(make_action())) == []
    assert check_fr3(case, make_obs(make_action())) == []
    assert check_fr4(case, make_obs(make_action())) == []


def test_fr2_listed_fields_stay_null() -> None:
    case = make_case(
        expected={"intent": "clarify", "null_fields": ["datetime_iso"]}, traces=("FR-2",)
    )
    assert passed_map(check_fr2(case, make_obs(_clarify()))) == {"fr2.null.datetime_iso": True}
    invented = make_obs(make_action())
    assert passed_map(check_fr2(case, invented)) == {"fr2.null.datetime_iso": False}


def test_fr2_without_null_fields_has_no_checks() -> None:
    assert check_fr2(make_case(traces=("FR-2",)), make_obs(_clarify())) == []


def test_fr3_expected_create_matches_the_local_clock_time() -> None:
    expected = {"intent": "create", "datetime_iso": "2026-11-06T09:00:00+00:00"}
    case = make_case(expected=expected, traces=("AC-3", "FR-3"))
    good = make_obs(make_action(datetime_iso="2026-11-06T09:00:00+00:00"))
    bad = make_obs(make_action(datetime_iso="2026-11-06T08:00:00+00:00"))
    assert passed_map(check_fr3(case, good))["fr3.clock"] is True
    assert passed_map(check_fr3(case, bad))["fr3.clock"] is False


def test_fr3_clock_is_compared_in_the_case_timezone() -> None:
    expected = {"intent": "create", "datetime_iso": "2027-03-14T09:00:00-04:00"}
    case = make_case(timezone=NY["timezone"], now=NY["now"], expected=expected, traces=("FR-3",))
    same_instant = make_obs(make_action(datetime_iso="2027-03-14T13:00:00+00:00"))
    assert passed_map(check_fr3(case, same_instant))["fr3.clock"] is True


def test_fr3_expected_clarify_has_no_datetime() -> None:
    case = make_case(expected={"intent": "clarify"}, traces=("AC-6", "FR-3"))
    assert passed_map(check_fr3(case, make_obs(_clarify())))["fr3.no_datetime"] is True
    assert passed_map(check_fr3(case, make_obs(make_action())))["fr3.no_datetime"] is False


def test_fr4_never_shifts_a_past_time_silently() -> None:
    case = make_case(expected={"intent": "clarify"}, traces=("AC-7", "FR-4"))
    assert passed_map(check_fr4(case, make_obs(_clarify())))["fr4.no_datetime"] is True
    shifted = make_obs(make_action())
    assert passed_map(check_fr4(case, shifted))["fr4.no_datetime"] is False


def test_fr4_a_created_time_must_be_in_the_future() -> None:
    case = make_case(traces=("FR-4",))
    past = make_obs(make_action(datetime_iso="2026-11-04T09:00:00+00:00"))
    assert passed_map(check_fr4(case, past))["fr4.future"] is False
