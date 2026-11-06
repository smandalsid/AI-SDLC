"""Layer 1: structural validation against the output schema (INV-1 to INV-8)."""

import pytest

from evaluators.common import JSON
from evaluators.schema import load_schema, run_structural
from harness_helpers import make_action, make_case, make_obs, make_reminder, passed_map

pytestmark = pytest.mark.covers(
    "INV-1", "INV-2", "INV-3", "INV-4", "INV-5", "INV-6", "INV-7", "INV-8", "FR-11"
)

SCHEMA = load_schema()


def _run(action: JSON, reminders: list[JSON] | None = None) -> dict[str, bool]:
    case = make_case(reminders=reminders)
    return passed_map(run_structural(case, make_obs(action), SCHEMA))


def test_a_valid_action_passes_all_eight_checks() -> None:
    result = _run(make_action())
    assert len(result) == 8 and all(result.values())


def test_not_json_object_fails() -> None:
    assert _run("not json")["inv1"] is False


def test_unknown_intent_breaks_inv1_and_inv2() -> None:
    result = _run(make_action(intent="delete"))
    assert result["inv1"] is False and result["inv2"] is False


def test_naive_datetime_breaks_inv3() -> None:
    assert _run(make_action(datetime_iso="2026-11-09T09:00:00"))["inv3"] is False


@pytest.mark.parametrize(("minutes", "ok"), [(0, False), (1, True), (1440, True), (1441, False)])
def test_snooze_minutes_range_inv4(minutes: int, ok: bool) -> None:
    action = make_action(
        intent="snooze",
        title=None,
        datetime_iso=None,
        target_reminder_id="r1",
        snooze_minutes=minutes,
    )
    assert _run(action, [make_reminder("r1")])["inv4"] is ok


def test_target_must_come_from_the_supplied_ids_inv5() -> None:
    action = make_action(intent="cancel", title=None, datetime_iso=None, target_reminder_id="zz")
    assert _run(action, [make_reminder("r1")])["inv5"] is False
    action["target_reminder_id"] = "r1"
    assert _run(action, [make_reminder("r1")])["inv5"] is True


def test_question_present_only_for_clarify_inv6() -> None:
    assert _run(make_action(clarification_question="when?"))["inv6"] is False
    missing = make_action(intent="clarify", title=None, datetime_iso=None)
    assert _run(missing)["inv6"] is False
    good = make_action(
        intent="clarify", title=None, datetime_iso=None, clarification_question="What time?"
    )
    assert _run(good)["inv6"] is True


def test_reason_present_only_for_refuse_inv7() -> None:
    assert _run(make_action(refusal_reason="unsafe"))["inv7"] is False
    missing = make_action(intent="refuse", title=None, datetime_iso=None)
    assert _run(missing)["inv7"] is False


def test_extra_field_breaks_inv8() -> None:
    assert _run({**make_action(), "extra": 1})["inv8"] is False


@pytest.mark.parametrize(
    ("action", "inv"),
    [
        (make_action(title=None), "inv1"),
        (
            make_action(
                intent="reschedule", title=None, datetime_iso=None, target_reminder_id="r1"
            ),
            "inv3",
        ),
        (make_action(intent="snooze", title=None, datetime_iso=None), "inv5"),
    ],
)
def test_missing_per_intent_field_fails_the_matching_invariant(
    action: dict[str, object], inv: str
) -> None:
    assert _run(action, [make_reminder("r1")])[inv] is False


def test_malformed_case_rejected_before_the_model_has_no_structural_checks() -> None:
    case = make_case(expected={"http_status": 422}, text="")
    assert run_structural(case, make_obs(None, status=422, model_calls=0), SCHEMA) == []


def test_missing_action_for_a_model_case_fails_inv1() -> None:
    results = run_structural(make_case(), make_obs(None, status=502), SCHEMA)
    assert [r.check_id for r in results] == ["inv1"] and results[0].passed is False


def test_results_carry_the_layer_and_requirement_id() -> None:
    result = run_structural(make_case(), make_obs(make_action()), SCHEMA)[0]
    assert result.layer == "structural" and result.requirement_ids
