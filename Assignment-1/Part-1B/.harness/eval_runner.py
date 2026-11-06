"""Single evaluation runner: dataset, application, three layers, aggregate, verdict."""

from __future__ import annotations

import argparse
import copy
import importlib
import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Protocol

from evaluators.common import JSON, CheckResult, Observation
from evaluators.properties import run_property_checks
from evaluators.schema import load_schema, run_structural
from evaluators.semantic import run_semantic
from infra import RETRY_DELAYS, RequestBudget, call_with_retry
from redact import redact_json, secrets_from_env
from scoring import Thresholds, aggregate, case_score, layer_score
from summarize import VerdictInputs, compute_verdict

MAX_TEXT = 1000
LAYERS = ("structural", "property", "semantic")
DEFAULT_FACTORY = "app.eval_adapter:build"


@dataclass(frozen=True)
class PreflightReport:
    ok: bool
    cause: str
    info: dict[str, str]


class CaseExecutor(Protocol):
    def preflight(self) -> PreflightReport: ...

    def execute(self, case: JSON, run_index: int) -> Observation: ...

    def sentinels(self) -> list[str]: ...

    def metadata(self) -> dict[str, str]: ...


@dataclass
class CaseResult:
    case_id: str
    category: str
    status: str
    runs: int
    traces: list[str]
    guardrail: bool
    scores: dict[str, float | None]
    checks: list[CheckResult]
    observations: list[Observation]
    infra_kind: str | None = None
    attempts: int = 0


@dataclass
class EvalReport:
    verdict: str
    cases: list[CaseResult]
    metrics: JSON
    requests_used: int
    results: JSON = field(default_factory=dict)


@dataclass(frozen=True)
class _Context:
    executor: CaseExecutor
    thresholds: Thresholds
    budget: RequestBudget
    sleep: Callable[[float], None]
    schema: JSON
    sentinels: list[str]


def resolve_case(case: JSON) -> JSON:
    """Copy of the case with `text_generate` expanded to text of exactly the requested length."""
    resolved = copy.deepcopy(case)
    generated = resolved["input"].pop("text_generate", None)
    if generated is not None:
        unit, length = generated["unit"], generated["length"]
        resolved["input"]["text"] = (unit * (length // len(unit) + 1))[:length]
    return resolved


def reaches_model(case: JSON) -> bool:
    text = case["input"].get("text")
    return isinstance(text, str) and bool(text.strip()) and len(text) <= MAX_TEXT


def is_guardrail_case(case: JSON) -> bool:
    return case["category"] == "adversarial" or any(t.startswith("GR-") for t in case["traces"])


def _served_check(obs: Observation, model: str) -> Observation:
    served = (obs.call or {}).get("model_served")
    if obs.infra_kind is None and served not in (None, model):
        return replace(obs, infra_kind="model_routing")
    return obs


def _result(case: JSON, status: str, observations: list[Observation], attempts: int) -> CaseResult:
    return CaseResult(
        case_id=case["id"],
        category=case["category"],
        status=status,
        runs=len(observations),
        traces=list(case["traces"]),
        guardrail=is_guardrail_case(case),
        scores={"structural": None, "property": None, "semantic": None, "case": None},
        checks=[],
        observations=observations,
        attempts=attempts,
    )


def _evaluate(
    case: JSON, observations: list[Observation], ctx: _Context, attempts: int
) -> CaseResult:
    th, obs = ctx.thresholds, observations[0]
    layers = {
        "structural": run_structural(case, obs, ctx.schema),
        "property": run_property_checks(case, obs, observations, ctx.sentinels, th.consistency_k),
        "semantic": run_semantic(case, obs, th.title_overlap_min, th.datetime_tolerance_seconds),
    }
    scores: dict[str, float | None] = {k: layer_score(v) for k, v in layers.items()}
    scores["case"] = case_score(
        scores["structural"], scores["property"], scores["semantic"], th.weights
    )
    checks = [c for name in LAYERS for c in layers[name]]
    out = _result(case, "PASS" if all(c.passed for c in checks) else "FAIL", observations, attempts)
    out.scores, out.checks = scores, checks
    return out


def _execute(ctx: _Context, case: JSON, run_index: int) -> Observation:
    obs = ctx.executor.execute(case, run_index)
    return _served_check(obs, ctx.thresholds.expected_model_id)


def _run_case(case: JSON, ctx: _Context) -> CaseResult:
    runs = ctx.thresholds.consistency_k if case.get("consistency") else 1
    takes_budget = reaches_model(case)
    observations: list[Observation] = []
    attempts = 0
    for index in range(1, runs + 1):
        outcome = call_with_retry(
            partial(_execute, ctx, case, index),
            budget=ctx.budget,
            takes_budget=takes_budget,
            max_retries=ctx.thresholds.infra_max_retries,
            delays=RETRY_DELAYS,
            sleep=ctx.sleep,
        )
        attempts += outcome.attempts
        if outcome.observation is None:
            return _result(case, "NOT_RUN", observations, attempts)
        observations.append(outcome.observation)
        if outcome.observation.infra_kind is not None:
            failed = _result(case, "INFRA_ERROR", observations, attempts)
            failed.infra_kind = outcome.observation.infra_kind
            return failed
    return _evaluate(case, observations, ctx, attempts)


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _layer_rates(scored: list[CaseResult]) -> dict[str, float | None]:
    rates: dict[str, float | None] = {}
    for layer in LAYERS:
        checks = [c for r in scored for c in r.checks if c.layer == layer]
        rates[layer] = (
            round(_rate(sum(c.passed for c in checks), len(checks)), 4) if checks else None
        )
    return rates


def _category_scores(scored: list[CaseResult]) -> dict[str, float]:
    by_category: dict[str, list[float]] = {}
    for r in scored:
        by_category.setdefault(r.category, []).append(r.scores["case"] or 0.0)
    return {name: aggregate(values) for name, values in by_category.items()}


def _failures(scored: list[CaseResult]) -> list[JSON]:
    return [
        {
            "gate": "eval",
            "case_id": r.case_id,
            "check_id": c.check_id,
            "requirement_ids": list(c.requirement_ids),
            "expected": c.expected,
            "observed": c.observed,
        }
        for r in scored
        for c in r.checks
        if not c.passed
    ]


def _verdict_inputs(
    results: list[CaseResult], scored: list[CaseResult], budget: RequestBudget, preflight_ok: bool
) -> JSON:
    structural = [r for r in scored if r.scores["structural"] is not None]
    guardrails = [r for r in scored if r.guardrail]
    infra = [r for r in results if r.status == "INFRA_ERROR"]
    return {
        "preflight_ok": preflight_ok,
        "not_run": sum(r.status == "NOT_RUN" for r in results),
        "cap_reached": budget.exhausted,
        "infra_share": len(infra) / len(results) if results else 0.0,
        "structural_rate": _rate(
            sum(r.scores["structural"] == 1.0 for r in structural), len(structural)
        ),
        "guardrail_rate": _rate(
            sum(all(c.passed for c in r.checks if c.layer != "semantic") for r in guardrails),
            len(guardrails),
        ),
        "aggregate": aggregate([r.scores["case"] or 0.0 for r in scored]),
        "consistency_failures": [
            r.case_id
            for r in scored
            if any(c.check_id == "fr9.identical" and not c.passed for c in r.checks)
        ],
    }


def _run_block(ctx: _Context, results: list[CaseResult], timestamp: str) -> JSON:
    served = sorted(
        {
            str(o.call["model_served"])
            for r in results
            for o in r.observations
            if o.call and o.call.get("model_served")
        }
    )
    w = ctx.thresholds.weights
    return {
        **ctx.executor.metadata(),
        "timestamp_utc": timestamp,
        "model_served": served,
        "request_count": ctx.budget.used,
        "threshold": {"aggregate_min": ctx.thresholds.aggregate_min},
        "scoring_formula": (
            f"{w.structural:.2f}*structural + {w.property:.2f}*property "
            f"+ {w.semantic:.2f}*semantic "
            "(weights redistributed over layers with applicable checks)"
        ),
    }


def _metrics(
    results: list[CaseResult],
    ctx: _Context,
    preflight: PreflightReport,
    mode: str,
    final: bool,
    timestamp: str,
) -> JSON:
    scored = [r for r in results if r.status in ("PASS", "FAIL")]
    inputs = _verdict_inputs(results, scored, ctx.budget, preflight.ok)
    verdict = compute_verdict(_as_inputs(inputs, ctx.thresholds, mode, final))
    return {
        "verdict": verdict,
        "verdict_inputs": inputs,
        "per_layer_pass_rate": _layer_rates(scored),
        "per_category_score": _category_scores(scored),
        "requests": {"used": ctx.budget.used, "cap": ctx.thresholds.live_request_max},
        "failures": _failures(scored),
        "infra_errors": [
            {"case_id": r.case_id, "kind": r.infra_kind, "attempts": r.attempts}
            for r in results
            if r.status == "INFRA_ERROR"
        ],
        "preflight": {"ok": preflight.ok, "cause": preflight.cause, "info": preflight.info},
        "run": _run_block(ctx, results, timestamp),
    }


def _as_inputs(raw: JSON, th: Thresholds, mode: str, final: bool) -> VerdictInputs:
    return VerdictInputs(
        preflight_ok=raw["preflight_ok"],
        not_run=raw["not_run"],
        cap_reached=raw["cap_reached"],
        infra_share=raw["infra_share"],
        infra_max_share=th.infra_max_share,
        final_requested=final,
        mode=mode,
        failed_gates=(),
        structural_rate=raw["structural_rate"],
        structural_min=th.structural_pass_min,
        guardrail_rate=raw["guardrail_rate"],
        guardrail_min=th.guardrail_pass_min,
        aggregate=raw["aggregate"],
        aggregate_min=th.aggregate_min,
        consistency_failures=tuple(raw["consistency_failures"]),
    )


def _case_record(r: CaseResult, secrets: list[str]) -> JSON:
    first = r.observations[0] if r.observations else None
    return redact_json(
        {
            "case_id": r.case_id,
            "category": r.category,
            "status": r.status,
            "runs": r.runs,
            "traces": r.traces,
            "scores": r.scores,
            "checks": [
                {
                    "layer": c.layer,
                    "id": c.check_id,
                    "requirement_ids": list(c.requirement_ids),
                    "passed": c.passed,
                }
                for c in r.checks
            ],
            "observed_action": first.action if first else None,
            "call": first.call if first else None,
        },
        secrets,
    )


def _write_outputs(
    results: list[CaseResult], metrics: JSON, mode: str, results_dir: Path, evidence_dir: Path
) -> JSON:
    secrets = secrets_from_env(os.environ)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "eval-metrics.json").write_text(json.dumps(metrics, indent=2))
    document = {
        "run": metrics["run"],
        "cases": [_case_record(r, secrets) for r in results],
        "infra_errors": metrics["infra_errors"],
    }
    text = json.dumps(redact_json(document, secrets), indent=2)
    (results_dir / "eval-results.json").write_text(text)
    if mode == "live":
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "eval-results.json").write_text(text)
        _write_recordings(results, results_dir / "recorded", secrets)
    return document


def _write_recordings(results: list[CaseResult], folder: Path, secrets: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for r in results:
        for index, obs in enumerate(r.observations, start=1):
            if obs.action is not None:
                (folder / f"{r.case_id}.{index}.json").write_text(
                    json.dumps(redact_json(obs.action, secrets), indent=2)
                )


def run_eval(
    dataset: JSON,
    executor: CaseExecutor,
    *,
    mode: str,
    thresholds: Thresholds,
    results_dir: Path,
    evidence_dir: Path,
    final_requested: bool = False,
    force_preflight: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    timestamp: str | None = None,
) -> EvalReport:
    cases = [resolve_case(c) for c in dataset["cases"]]
    stamp = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    preflight = PreflightReport(True, "", {})
    if mode == "live" or force_preflight:
        preflight = executor.preflight()
    ctx = _Context(
        executor,
        thresholds,
        RequestBudget(thresholds.live_request_max),
        sleep,
        load_schema(),
        executor.sentinels(),
    )
    if preflight.ok:
        with ThreadPoolExecutor(max_workers=thresholds.eval_concurrency) as pool:
            results = list(pool.map(lambda c: _run_case(c, ctx), cases))
    else:
        results = [_result(c, "NOT_RUN", [], 0) for c in cases]
    metrics = _metrics(results, ctx, preflight, mode, final_requested, stamp)
    document = _write_outputs(results, metrics, mode, results_dir, evidence_dir)
    return EvalReport(metrics["verdict"], results, metrics, ctx.budget.used, document)


class _UnavailableExecutor:
    """Stands in when the application adapter cannot be imported: preflight reports why."""

    def __init__(self, cause: str) -> None:
        self._cause = cause

    def preflight(self) -> PreflightReport:
        return PreflightReport(False, self._cause, {})

    def execute(self, case: JSON, run_index: int) -> Observation:
        raise RuntimeError("executor unavailable")

    def sentinels(self) -> list[str]:
        return []

    def metadata(self) -> dict[str, str]:
        return {}


def _load_executor(spec: str, mode: str, recordings: Path | None) -> CaseExecutor:
    module_name, _, function = spec.partition(":")
    try:
        factory = getattr(importlib.import_module(module_name), function)
    except (ImportError, AttributeError) as error:
        return _UnavailableExecutor(f"executor {spec} unavailable: {error}")
    executor: CaseExecutor = factory(mode=mode, recordings_dir=recordings)
    return executor


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("live", "replay"), required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, default=Path("evidence"))
    parser.add_argument("--recordings-dir", type=Path, default=Path("evals/recorded"))
    parser.add_argument("--dataset", type=Path, default=Path("evals/dataset.json"))
    parser.add_argument("--executor-factory", default=DEFAULT_FACTORY)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args(argv)
    executor = _load_executor(args.executor_factory, args.mode, args.recordings_dir)
    report = run_eval(
        json.loads(args.dataset.read_text()),
        executor,
        mode=args.mode,
        thresholds=Thresholds.from_env(os.environ),
        results_dir=args.results_dir,
        evidence_dir=args.evidence_dir,
        final_requested=args.final,
        force_preflight=isinstance(executor, _UnavailableExecutor),
    )
    pre = report.metrics["preflight"]
    print(f"eval verdict: {report.verdict}; requests {report.requests_used}")
    if not pre["ok"]:
        print(f"preflight failed: {pre['cause']}")
    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
