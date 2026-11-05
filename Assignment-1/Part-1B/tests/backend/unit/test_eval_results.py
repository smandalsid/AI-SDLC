"""Shape and safety of evidence/eval-results.json (FR-15, AC-33)."""

import json
from pathlib import Path

import pytest

from eval_runner import PreflightReport, run_eval
from evaluators.common import JSON, Observation
from harness_helpers import make_action, make_case, make_obs, thresholds_env
from scoring import Thresholds

pytestmark = pytest.mark.covers("FR-15", "AC-33")

T = Thresholds.from_env(thresholds_env())
TOKEN = "ghp_" + "B" * 36
EXPECTED = {"intent": "create", "title": "pay rent", "datetime_iso": "2026-11-09T09:00:00+00:00"}


class _Executor:
    def preflight(self) -> PreflightReport:
        return PreflightReport(ok=True, cause="", info={})

    def execute(self, case: JSON, run_index: int) -> Observation:
        text = case["input"]["text"]
        if not isinstance(text, str) or not text.strip():
            return make_obs(None, status=422, model_calls=0)
        action = make_action(title=f"pay rent {TOKEN}", datetime_iso=EXPECTED["datetime_iso"])
        call = {
            "model_served": "gpt-6-luna",
            "input_tokens": 1,
            "output_tokens": 2,
            "duration_ms": 3,
        }
        return make_obs(action, call=call)

    def sentinels(self) -> list[str]:
        return ["PROMPT-CANARY"]

    def metadata(self) -> dict[str, str]:
        return {
            "model_requested": "gpt-6-luna",
            "reasoning_effort": "low",
            "sdk_version": "1.0.28",
            "runtime_version": "1.0.105",
        }


def _results(tmp_path: Path) -> tuple[dict[str, object], str]:
    cases = [
        make_case("N01", "normal", expected=EXPECTED, traces=("AC-1", "FR-1"), consistency=True),
        make_case(
            "X02", "malformed", text="", expected={"http_status": 422}, traces=("AC-15", "FR-8")
        ),
    ]
    run_eval(
        {"version": 1, "cases": cases},
        _Executor(),
        mode="live",
        thresholds=T,
        results_dir=tmp_path / "res",
        evidence_dir=tmp_path / "ev",
        sleep=lambda s: None,
        timestamp="20261105T101500Z",
    )
    path = tmp_path / "ev" / "eval-results.json"
    return json.loads(path.read_text()), path.read_text()


def test_run_block_records_model_settings_threshold_and_formula(tmp_path: Path) -> None:
    data, _ = _results(tmp_path)
    run = data["run"]
    assert run["timestamp_utc"] == "20261105T101500Z"  # type: ignore[index]  # JSON test
    assert run["model_requested"] == "gpt-6-luna"  # type: ignore[index]  # JSON test
    assert run["model_served"] == ["gpt-6-luna"]  # type: ignore[index]  # JSON test
    assert run["reasoning_effort"] == "low" and run["sdk_version"] == "1.0.28"  # type: ignore[index]  # JSON test
    assert run["runtime_version"] == "1.0.105" and run["request_count"] == 3  # type: ignore[index]  # JSON test
    assert run["threshold"] == {"aggregate_min": 0.85}  # type: ignore[index]  # JSON test
    assert "0.30*structural" in run["scoring_formula"]  # type: ignore[index]  # JSON test


def test_each_case_records_runs_traces_scores_and_checks(tmp_path: Path) -> None:
    data, _ = _results(tmp_path)
    by_id = {c["case_id"]: c for c in data["cases"]}  # type: ignore[attr-defined]  # JSON test
    n01 = by_id["N01"]
    assert n01["runs"] == 3 and n01["traces"] == ["AC-1", "FR-1"] and n01["category"] == "normal"
    assert set(n01["scores"]) == {"structural", "property", "semantic", "case"}
    check = n01["checks"][0]
    assert {"layer", "id", "requirement_ids", "passed"} <= set(check)
    assert n01["call"]["model_served"] == "gpt-6-luna"
    assert by_id["X02"]["runs"] == 1 and by_id["X02"]["scores"]["structural"] is None
    assert data["infra_errors"] == []


def test_no_secret_or_prompt_text_appears_anywhere(tmp_path: Path) -> None:
    _, text = _results(tmp_path)
    assert TOKEN not in text and "PROMPT-CANARY" not in text
    recorded = (tmp_path / "res" / "recorded" / "N01.1.json").read_text()
    assert TOKEN not in recorded
