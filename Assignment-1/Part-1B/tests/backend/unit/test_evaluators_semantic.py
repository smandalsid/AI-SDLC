"""Layer 3: deterministic semantic and quality checks (FR-11)."""

import pytest

from evaluators.common import JSON
from evaluators.semantic import run_semantic, title_overlap, tokens
from harness_helpers import make_action, make_case, make_obs, passed_map

pytestmark = pytest.mark.covers("FR-11", "AC-2", "AC-38")

TITLE_MIN, TOLERANCE = 0.6, 60


def _clarify(question: str) -> JSON:
    return make_action(
        intent="clarify", title=None, datetime_iso=None, clarification_question=question
    )


def test_tokenisation_is_lowercase_alphanumeric_without_stop_words() -> None:
    assert tokens("Call the vendor!") == {"call", "the", "vendor"}


def test_title_overlap_is_measured_against_the_ground_truth() -> None:
    assert title_overlap("Call vendor", "call the vendor") == pytest.approx(2 / 3)
    assert title_overlap("buy milk", "call the vendor") == 0.0


def test_title_fidelity_ac2_and_ac38() -> None:
    case = make_case(expected={"intent": "create", "title": "call the vendor"})
    good = make_obs(make_action(title="Call vendor"))
    bad = make_obs(make_action(title="buy milk"))
    assert passed_map(run_semantic(case, good, TITLE_MIN, TOLERANCE))["semantic.title"] is True
    assert passed_map(run_semantic(case, bad, TITLE_MIN, TOLERANCE))["semantic.title"] is False
    sensitive = make_case(expected={"intent": "create", "title": "take my blood pressure pills"})
    kept = make_obs(make_action(title="Take blood pressure pills"))
    assert passed_map(run_semantic(sensitive, kept, TITLE_MIN, TOLERANCE))["semantic.title"] is True


def test_missing_title_fails_title_fidelity() -> None:
    case = make_case(expected={"intent": "create", "title": "call the vendor"})
    none = make_obs(make_action(title=None))
    assert passed_map(run_semantic(case, none, TITLE_MIN, TOLERANCE))["semantic.title"] is False


@pytest.mark.parametrize(
    ("observed", "ok"),
    [
        ("2026-11-10T18:00:30+00:00", True),
        ("2026-11-10T18:01:00+00:00", True),
        ("2026-11-10T18:01:01+00:00", False),
        ("2026-11-10T23:30:00+05:30", True),
    ],
)
def test_datetime_accuracy_is_within_the_tolerance_as_an_instant(observed: str, ok: bool) -> None:
    case = make_case(expected={"intent": "create", "datetime_iso": "2026-11-10T18:00:00+00:00"})
    result = passed_map(
        run_semantic(case, make_obs(make_action(datetime_iso=observed)), TITLE_MIN, TOLERANCE)
    )
    assert result["semantic.datetime"] is ok


def test_missing_datetime_fails_datetime_accuracy() -> None:
    case = make_case(expected={"intent": "create", "datetime_iso": "2026-11-10T18:00:00+00:00"})
    result = run_semantic(case, make_obs(make_action(datetime_iso=None)), TITLE_MIN, TOLERANCE)
    assert passed_map(result)["semantic.datetime"] is False


def test_clarification_rubric_keyword_single_question_and_nothing_invented() -> None:
    rubric = {"names_field": ["time", "when"], "single_question": True, "invents_nothing": True}
    expected = {"intent": "clarify", "null_fields": ["datetime_iso"], "rubric": rubric}
    case = make_case(expected=expected)
    good = passed_map(
        run_semantic(
            case, make_obs(_clarify("What time should I remind you?")), TITLE_MIN, TOLERANCE
        )
    )
    assert set(good.values()) == {True}
    two = passed_map(
        run_semantic(case, make_obs(_clarify("What time? Or when?")), TITLE_MIN, TOLERANCE)
    )
    assert two["semantic.rubric.single_question"] is False
    off = passed_map(
        run_semantic(case, make_obs(_clarify("Which day works?")), TITLE_MIN, TOLERANCE)
    )
    assert off["semantic.rubric.keyword"] is False
    invented = make_obs(make_action(clarification_question="What time?", intent="clarify"))
    result = passed_map(run_semantic(case, invented, TITLE_MIN, TOLERANCE))
    assert result["semantic.rubric.invents_nothing"] is False


def test_rubric_fails_when_no_question_was_asked() -> None:
    case = make_case(expected={"intent": "clarify", "rubric": {"names_field": ["time"]}})
    result = passed_map(run_semantic(case, make_obs(make_action()), TITLE_MIN, TOLERANCE))
    assert result["semantic.rubric.keyword"] is False


def test_no_ground_truth_or_rubric_means_no_semantic_checks() -> None:
    case = make_case(expected={"intent": "cancel", "target_reminder_id": "r2"})
    assert run_semantic(case, make_obs(make_action()), TITLE_MIN, TOLERANCE) == []
