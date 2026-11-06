"""FR-12 scoring formula and the threshold loader (AC-31)."""

import pytest

from evaluators.common import CheckResult
from harness_helpers import thresholds_env
from scoring import Thresholds, Weights, aggregate, case_score, layer_score

pytestmark = pytest.mark.covers("FR-12", "AC-31")

W = Weights.from_env(thresholds_env())


def _check(passed: bool) -> CheckResult:
    return CheckResult("property", "c", ("FR-1",), passed, "e", "o")


def test_weights_come_from_the_environment() -> None:
    assert (W.structural, W.property, W.semantic) == (0.30, 0.40, 0.30)


def test_case_score_with_all_layers() -> None:
    assert case_score(1.0, 0.5, 0.0, W) == 0.5


def test_case_score_without_semantic_matches_ac31() -> None:
    assert case_score(1.0, 0.5, None, W) == 0.7143


def test_case_score_redistributes_when_structural_is_missing() -> None:
    assert case_score(None, 0.5, None, W) == 0.5
    assert case_score(None, 1.0, 1.0, W) == 1.0


def test_case_score_with_no_applicable_layer_is_zero() -> None:
    assert case_score(None, None, None, W) == 0.0


def test_layer_score_is_the_fraction_of_passed_checks() -> None:
    assert layer_score([_check(True), _check(False)]) == 0.5
    assert layer_score([_check(True)]) == 1.0
    assert layer_score([]) is None


def test_aggregate_is_the_mean() -> None:
    assert aggregate([1.0, 0.5]) == 0.75
    assert aggregate([]) == 0.0


def test_thresholds_load_from_the_environment() -> None:
    t = Thresholds.from_env(thresholds_env())
    assert t.aggregate_min == 0.85
    assert t.consistency_k == 3
    assert t.live_request_max == 60
    assert t.infra_max_retries == 2
    assert t.expected_model_id == "gpt-6-luna"


def test_missing_threshold_key_fails_fast() -> None:
    env = thresholds_env()
    del env["AGGREGATE_MIN"]
    with pytest.raises(KeyError):
        Thresholds.from_env(env)
