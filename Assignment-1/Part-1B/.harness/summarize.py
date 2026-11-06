"""Verdict, summary.json, console summary and the run-table row (spec FR-13, FR-16)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from evaluators.common import JSON

GATES = ("integrity", "lint", "security", "test", "eval")
_ROW = re.compile(r"^\| \d+ \|", re.MULTILINE)
_HEADING = re.compile(r"^## .*$", re.MULTILINE)


@dataclass(frozen=True)
class VerdictInputs:
    preflight_ok: bool
    not_run: int
    cap_reached: bool
    infra_share: float
    infra_max_share: float
    final_requested: bool
    mode: str
    failed_gates: tuple[str, ...]
    structural_rate: float
    structural_min: float
    guardrail_rate: float
    guardrail_min: float
    aggregate: float
    aggregate_min: float
    consistency_failures: tuple[str, ...]


def compute_verdict(v: VerdictInputs) -> str:
    """First matching rule wins: INVALID, then FAIL, then PASS."""
    if not v.preflight_ok or v.not_run > 0 or v.cap_reached:
        return "INVALID"
    if v.infra_share > v.infra_max_share or (v.final_requested and v.mode != "live"):
        return "INVALID"
    if v.failed_gates or v.consistency_failures:
        return "FAIL"
    if v.structural_rate < v.structural_min or v.guardrail_rate < v.guardrail_min:
        return "FAIL"
    return "FAIL" if v.aggregate < v.aggregate_min else "PASS"


def _gate_statuses(out: Path) -> dict[str, tuple[str, int | None]]:
    statuses: dict[str, tuple[str, int | None]] = {}
    for gate in GATES:
        file = out / f"{gate}.exitcode"
        if not file.exists():
            statuses[gate] = ("NOT_RUN", None)
            continue
        code = int(file.read_text().strip())
        statuses[gate] = ("PASS" if code == 0 else "FAIL", code)
    return statuses


def _verdict_inputs(
    metrics: JSON | None,
    failed_gates: tuple[str, ...],
    mode: str,
    final_requested: bool,
    env: Mapping[str, str],
) -> VerdictInputs:
    raw = (metrics or {}).get("verdict_inputs", {})
    return VerdictInputs(
        preflight_ok=raw.get("preflight_ok", True),
        not_run=raw.get("not_run", 0),
        cap_reached=raw.get("cap_reached", False),
        infra_share=raw.get("infra_share", 0.0),
        infra_max_share=float(env["INFRA_MAX_SHARE"]),
        final_requested=final_requested,
        mode=mode,
        failed_gates=failed_gates,
        structural_rate=raw.get("structural_rate", 1.0),
        structural_min=float(env["STRUCTURAL_PASS_MIN"]),
        guardrail_rate=raw.get("guardrail_rate", 1.0),
        guardrail_min=float(env["GUARDRAIL_PASS_MIN"]),
        aggregate=raw.get("aggregate", 0.0),
        aggregate_min=float(env["AGGREGATE_MIN"]),
        consistency_failures=tuple(raw.get("consistency_failures", ())),
    )


def _gate_failures(statuses: Mapping[str, tuple[str, int | None]], has_metrics: bool) -> list[JSON]:
    failures: list[JSON] = []
    for gate, (status, code) in statuses.items():
        if status == "PASS" or (gate == "eval" and has_metrics):
            continue
        observed = "not run" if code is None else f"exit code {code}"
        failures.append(
            {
                "gate": gate,
                "case_id": None,
                "requirement_ids": [],
                "expected": "exit code 0",
                "observed": observed,
            }
        )
    return failures


def build_summary(
    results_dir: Path,
    mode: str,
    timestamp: str,
    *,
    final_requested: bool = False,
    env: Mapping[str, str] | None = None,
) -> JSON:
    env = os.environ if env is None else env
    statuses = _gate_statuses(results_dir)
    metrics_file = results_dir / "eval-metrics.json"
    metrics = json.loads(metrics_file.read_text()) if metrics_file.exists() else None
    failures = _gate_failures(statuses, metrics is not None)
    failed = tuple(f["gate"] for f in failures)
    verdict = compute_verdict(_verdict_inputs(metrics, failed, mode, final_requested, env))
    raw = (metrics or {}).get("verdict_inputs", {})
    return {
        "timestamp_utc": timestamp,
        "mode": mode,
        "verdict": verdict,
        "results_dir": str(results_dir),
        "threshold": {"aggregate_min": float(env["AGGREGATE_MIN"])},
        "gates": [{"name": g, "status": s, "exit_code": c} for g, (s, c) in statuses.items()],
        "failures": failures + (metrics or {}).get("failures", []),
        "eval": {
            "per_layer_pass_rate": (metrics or {}).get("per_layer_pass_rate", {}),
            "per_category_score": (metrics or {}).get("per_category_score", {}),
            "aggregate": raw.get("aggregate"),
            "guardrail_pass_rate": raw.get("guardrail_rate"),
            "infra_error_share": raw.get("infra_share"),
            "requests": (metrics or {}).get("requests", {"used": 0, "cap": 0}),
        },
        "run": (metrics or {}).get("run", {}),
        "artifacts": sorted(p.name for p in results_dir.iterdir() if p.is_file()),
    }


def format_console(summary: JSON) -> str:
    ev = summary["eval"]
    lines = [f"Verdict: {summary['verdict']} ({summary['mode']} run {summary['timestamp_utc']})"]
    lines += [f"  gate {g['name']}: {g['status']}" for g in summary["gates"]]
    lines += [f"  layer {k}: pass rate {v}" for k, v in ev["per_layer_pass_rate"].items()]
    lines += [f"  category {k}: score {v}" for k, v in ev["per_category_score"].items()]
    lines.append(
        f"  aggregate: {ev['aggregate']} (threshold {summary['threshold']['aggregate_min']})"
    )
    lines.append(f"  requests: {ev['requests']['used']}/{ev['requests']['cap']}")
    lines += [
        f"  failure: {f['gate']} {f.get('case_id') or ''} {f['expected']} -> {f['observed']}"
        for f in summary["failures"]
    ]
    return "\n".join(lines)


def _row(number: int, summary: JSON) -> str:
    run, ev = summary["run"], summary["eval"]
    served = ",".join(run.get("model_served", []))
    model = (
        f"{run.get('model_requested', 'n/a')} ({served}) / "
        f"{run.get('reasoning_effort', 'n/a')} / sdk {run.get('sdk_version', 'n/a')}"
    )
    gates = " ".join(f"{g['name']}:{g['status']}" for g in summary["gates"])
    shown = (
        f"aggregate {ev['aggregate']}, guardrail {ev['guardrail_pass_rate']}, "
        f"infra {ev['infra_error_share']}"
    )
    minimum = summary["threshold"]["aggregate_min"]
    formula = f"aggregate >= {minimum}; weighted structural/property/semantic"
    requests = f"{ev['requests']['used']}/{ev['requests']['cap']}"
    cells = [
        number,
        summary["timestamp_utc"],
        summary["mode"],
        model,
        requests,
        formula,
        gates,
        shown,
        summary["verdict"],
        summary["results_dir"],
    ]
    return "| " + " | ".join(str(c) for c in cells) + " |"


def append_run_row(log_path: Path, summary: JSON) -> None:
    """Append one row to the end of the run table; refuse if the table is not the last section."""
    text = log_path.read_text()
    headings = _HEADING.findall(text)
    if not headings or "run table" not in headings[-1].lower():
        raise ValueError("the run table must be the last section of the harness log")
    if not text.endswith("\n"):
        text += "\n"
    number = len(_ROW.findall(text)) + 1
    log_path.write_text(text + _row(number, summary) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--mode", required=True, choices=("live", "replay"))
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--timestamp", default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    args = parser.parse_args(argv)
    summary = build_summary(args.results_dir, args.mode, args.timestamp, final_requested=args.final)
    (args.results_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(format_console(summary))
    if not args.dry_run:
        append_run_row(args.log, summary)
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
