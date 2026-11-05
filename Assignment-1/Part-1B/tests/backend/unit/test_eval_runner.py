"""Evaluation runner behaviour with a fake executor (FR-9, FR-14, FR-15, MEC-17..19)."""

import threading
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from eval_runner import (
    EvalReport,
    PreflightReport,
    is_guardrail_case,
    reaches_model,
    resolve_case,
    run_eval,
)
from evaluators.common import JSON, Observation
from harness_helpers import make_action, make_case, make_obs, thresholds_env
from scoring import Thresholds

pytestmark = pytest.mark.covers(
    "FR-9", "FR-14", "FR-15", "AC-28", "AC-29", "AC-30", "MEC-17", "MEC-18", "MEC-19"
)

T = Thresholds.from_env(thresholds_env())
CALL = {
    "model_served": "mai-code-1.1-flash",
    "input_tokens": 10,
    "output_tokens": 5,
    "duration_ms": 100,
}
GOOD = {"intent": "create", "title": "pay rent", "datetime_iso": "2026-11-09T09:00:00+00:00"}
Script = Callable[[JSON, int], Observation]


def _case(case_id: str, *, consistency: bool = False) -> JSON:
    return make_case(
        case_id,
        "normal",
        text="remind me to pay rent next Monday",
        consistency=consistency,
        expected=GOOD,
        traces=("AC-1", "FR-1"),
    )


def _dataset(extra: list[JSON] | None = None) -> JSON:
    malformed = make_case(
        "X02", "malformed", text="", expected={"http_status": 422}, traces=("AC-15", "FR-8")
    )
    cases = [_case("N01"), _case("N02", consistency=True), malformed, *(extra or [])]
    return {"version": 1, "cases": cases}


def _oracle(case: JSON, run_index: int) -> Observation:
    text = case["input"]["text"]
    if not isinstance(text, str) or not text.strip():
        return make_obs(None, status=422, model_calls=0)
    exp = case["expected"]
    action = make_action(title=exp.get("title"), datetime_iso=exp.get("datetime_iso"))
    return make_obs(action, call=CALL)


class FakeExecutor:
    def __init__(
        self, script: Script = _oracle, *, preflight_ok: bool = True, delay: float = 0.0
    ) -> None:
        self.script, self.ok, self.delay = script, preflight_ok, delay
        self.calls: list[tuple[str, int]] = []
        self.preflight_called = False
        self.active = self.max_active = 0
        self._lock = threading.Lock()

    def preflight(self) -> PreflightReport:
        self.preflight_called = True
        return PreflightReport(ok=self.ok, cause="" if self.ok else "not authenticated", info={})

    def execute(self, case: JSON, run_index: int) -> Observation:
        with self._lock:
            self.calls.append((case["id"], run_index))
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(self.delay)
        try:
            return self.script(case, run_index)
        finally:
            with self._lock:
                self.active -= 1

    def sentinels(self) -> list[str]:
        return ["CANARY"]

    def metadata(self) -> dict[str, str]:
        return {
            "model_requested": "mai-code-1.1-flash",
            "reasoning_effort": "low",
            "sdk_version": "1.0.28",
            "runtime_version": "1.0.105",
        }


def _run(
    tmp_path: Path, executor: FakeExecutor | None = None, **kw: JSON
) -> tuple[EvalReport, FakeExecutor]:
    ex = executor or FakeExecutor()
    kw.setdefault("mode", "live")
    kw.setdefault("thresholds", T)
    sleeps: list[float] = kw.pop("sleeps", [])
    dataset = kw.pop("dataset", _dataset())
    report = run_eval(
        dataset,
        ex,
        results_dir=tmp_path / "res",
        evidence_dir=tmp_path / "ev",
        sleep=sleeps.append,
        **kw,
    )
    return report, ex


def _status(report: EvalReport, case_id: str) -> str:
    return next(c.status for c in report.cases if c.case_id == case_id)


def test_text_generate_expands_to_the_exact_length_without_mutating_the_case() -> None:
    case = {"id": "X01", "input": {"text_generate": {"unit": "abc ", "length": 1001}}}
    resolved = resolve_case(case)
    assert len(resolved["input"]["text"]) == 1001
    assert "text" not in case["input"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", False),
        ("   ", False),
        (12345, False),
        ("x" * 1001, False),
        ("x" * 1000, True),
        ("hi", True),
    ],
)
def test_only_valid_text_up_to_1000_characters_reaches_the_model(
    text: object, expected: bool
) -> None:
    assert reaches_model({"input": {"text": text}}) is expected


def test_guardrail_case_is_adversarial_or_traces_a_gr_id() -> None:
    assert is_guardrail_case({"category": "adversarial", "traces": ["AC-8"]}) is True
    assert is_guardrail_case({"category": "normal", "traces": ["GR-4"]}) is True
    assert is_guardrail_case({"category": "normal", "traces": ["FR-1"]}) is False


def test_a_clean_live_run_passes_and_uses_the_expected_number_of_requests(tmp_path: Path) -> None:
    report, ex = _run(tmp_path)
    assert report.verdict == "PASS" and report.requests_used == 4
    assert report.metrics["verdict_inputs"]["aggregate"] == 1.0
    assert ex.preflight_called is True
    assert (tmp_path / "res" / "eval-metrics.json").exists()


def test_consistency_cases_run_k_times_and_malformed_cases_cost_nothing(tmp_path: Path) -> None:
    report, ex = _run(tmp_path)
    assert sorted(c for c in ex.calls if c[0] == "N02") == [("N02", 1), ("N02", 2), ("N02", 3)]
    assert sorted(c for c in ex.calls if c[0] == "N01") == [("N01", 1)]
    assert next(c.runs for c in report.cases if c.case_id == "N02") == 3


def test_a_differing_consistency_case_fails_the_run(tmp_path: Path) -> None:
    def script(case: JSON, run_index: int) -> Observation:
        if case["id"] == "N02" and run_index == 2:
            return make_obs(make_action(datetime_iso="2026-11-10T09:00:00+00:00"), call=CALL)
        return _oracle(case, run_index)

    report, _ = _run(tmp_path, FakeExecutor(script))
    assert report.verdict == "FAIL"
    assert report.metrics["verdict_inputs"]["consistency_failures"] == ["N02"]


def test_infra_error_is_retried_and_the_case_still_passes(tmp_path: Path) -> None:
    state = {"n": 0}

    def script(case: JSON, run_index: int) -> Observation:
        if case["id"] == "N01":
            state["n"] += 1
            if state["n"] == 1:
                return make_obs(None, status=503, infra_kind="timeout")
        return _oracle(case, run_index)

    sleeps: list[float] = []
    report, _ = _run(tmp_path, FakeExecutor(script), sleeps=sleeps)
    assert _status(report, "N01") == "PASS" and sleeps == [2.0]
    assert report.requests_used == 5


def test_exhausted_retries_give_infra_error_and_an_invalid_run(tmp_path: Path) -> None:
    def script(case: JSON, run_index: int) -> Observation:
        if case["id"] == "N01":
            return make_obs(None, status=503, infra_kind="timeout")
        return _oracle(case, run_index)

    sleeps: list[float] = []
    report, _ = _run(tmp_path, FakeExecutor(script), sleeps=sleeps)
    assert _status(report, "N01") == "INFRA_ERROR" and sleeps == [2.0, 6.0]
    assert report.verdict == "INVALID"
    assert report.metrics["infra_errors"][0] == {"case_id": "N01", "kind": "timeout", "attempts": 3}


def test_an_infra_error_in_a_consistency_run_makes_the_case_infra_error(tmp_path: Path) -> None:
    def script(case: JSON, run_index: int) -> Observation:
        if case["id"] == "N02" and run_index == 2:
            return make_obs(None, status=503, infra_kind="rpc")
        return _oracle(case, run_index)

    report, _ = _run(tmp_path, FakeExecutor(script))
    assert _status(report, "N02") == "INFRA_ERROR"


def test_a_served_model_different_from_the_configured_one_is_model_routing(tmp_path: Path) -> None:
    def script(case: JSON, run_index: int) -> Observation:
        obs = _oracle(case, run_index)
        if obs.call:
            return make_obs(obs.action, call={**CALL, "model_served": "gpt-x"})
        return obs

    report, _ = _run(tmp_path, FakeExecutor(script))
    assert _status(report, "N01") == "INFRA_ERROR"
    assert report.metrics["infra_errors"][0]["kind"] == "model_routing"


def test_request_cap_stops_the_run_and_marks_cases_not_run(tmp_path: Path) -> None:
    report, _ = _run(tmp_path, thresholds=replace(T, live_request_max=2))
    assert report.requests_used == 2 and report.verdict == "INVALID"
    assert any(c.status == "NOT_RUN" for c in report.cases)
    assert report.metrics["verdict_inputs"]["cap_reached"] is True


def test_failed_preflight_is_invalid_with_zero_requests(tmp_path: Path) -> None:
    report, ex = _run(tmp_path, FakeExecutor(preflight_ok=False))
    assert report.verdict == "INVALID" and ex.calls == [] and report.requests_used == 0
    assert all(c.status == "NOT_RUN" for c in report.cases)
    assert report.metrics["verdict_inputs"]["preflight_ok"] is False


def test_only_live_runs_write_the_evidence_results(tmp_path: Path) -> None:
    _run(tmp_path, mode="live")
    assert (tmp_path / "ev" / "eval-results.json").exists()
    assert (tmp_path / "res" / "recorded" / "N01.1.json").exists()


def test_replay_writes_only_under_the_results_directory(tmp_path: Path) -> None:
    _, ex = _run(tmp_path, mode="replay")
    assert not (tmp_path / "ev" / "eval-results.json").exists()
    assert (tmp_path / "res" / "eval-metrics.json").exists()
    assert ex.preflight_called is False


def test_a_final_result_from_a_replay_run_is_invalid(tmp_path: Path) -> None:
    report, _ = _run(tmp_path, mode="replay", final_requested=True)
    assert report.verdict == "INVALID"


def test_concurrency_never_exceeds_the_configured_limit(tmp_path: Path) -> None:
    extra = [_case(f"N{n}") for n in range(10, 16)]
    ex = FakeExecutor(delay=0.02)
    _run(tmp_path, ex, dataset=_dataset(extra))
    assert 1 <= ex.max_active <= T.eval_concurrency


def test_an_application_failure_is_a_failed_case_not_infrastructure(tmp_path: Path) -> None:
    def script(case: JSON, run_index: int) -> Observation:
        if case["id"] == "N01":
            return make_obs(None, status=502, applied=None, call=CALL)
        return _oracle(case, run_index)

    report, _ = _run(tmp_path, FakeExecutor(script))
    assert _status(report, "N01") == "FAIL" and report.verdict == "FAIL"
    assert report.metrics["verdict_inputs"]["structural_rate"] < 1.0
