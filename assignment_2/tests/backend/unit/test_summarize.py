"""summary.json, console summary and the run-table row (FR-16, MEC-25)."""

import json
from pathlib import Path

import pytest

from harness_helpers import thresholds_env
from summarize import append_run_row, build_summary, format_console, main

pytestmark = pytest.mark.covers("FR-16", "AC-32")

TABLE_HEADER = (
    "| run | timestamp_utc | mode | model / effort / sdk | requests |"
    " threshold / formula | gates | eval | verdict | results_dir |\n"
    "|-----|---------------|------|----------------------|----------|"
    "---------------------|-------|------|---------|-------------|\n"
)

LOG = (
    "# Harness Log\n\n## 1. Human Approval\n\ntext\n\n"
    "## 7. Final human decision (ACCEPT or REJECT)\n\n_pending_\n\n"
    "## 8. Run table\n\n" + TABLE_HEADER
)

METRICS = {
    "verdict_inputs": {
        "preflight_ok": True,
        "not_run": 0,
        "cap_reached": False,
        "infra_share": 0.0,
        "structural_rate": 1.0,
        "guardrail_rate": 1.0,
        "aggregate": 0.94,
        "consistency_failures": [],
    },
    "per_layer_pass_rate": {"structural": 1.0, "property": 0.96, "semantic": 0.93},
    "per_category_score": {"normal": 0.95},
    "requests": {"used": 47, "cap": 60},
    "failures": [
        {
            "gate": "eval",
            "case_id": "N03",
            "requirement_ids": ["FR-3"],
            "expected": "09:00",
            "observed": "08:00",
        }
    ],
    "run": {
        "model_requested": "gpt-6-luna",
        "model_served": ["gpt-6-luna"],
        "reasoning_effort": "low",
        "sdk_version": "1.0.28",
    },
}


def _results(tmp_path: Path, codes: dict[str, int], metrics: dict[str, object] | None) -> Path:
    out = tmp_path / "res"
    out.mkdir()
    for gate, code in codes.items():
        (out / f"{gate}.exitcode").write_text(str(code))
    if metrics is not None:
        (out / "eval-metrics.json").write_text(json.dumps(metrics))
    return out


ALL_OK = {"integrity": 0, "lint": 0, "security": 0, "test": 0, "eval": 0}


def test_summary_of_a_green_run(tmp_path: Path) -> None:
    out = _results(tmp_path, ALL_OK, METRICS)
    summary = build_summary(out, "live", "20261105T101500Z", env=thresholds_env())
    assert summary["verdict"] == "PASS"
    assert [g["name"] for g in summary["gates"]] == [
        "integrity",
        "lint",
        "security",
        "test",
        "eval",
    ]
    assert all(g["status"] == "PASS" for g in summary["gates"])
    assert summary["eval"]["aggregate"] == 0.94
    assert summary["eval"]["requests"] == {"used": 47, "cap": 60}
    assert summary["eval"]["per_layer_pass_rate"]["property"] == 0.96


def test_failed_gate_is_listed_with_expected_and_observed(tmp_path: Path) -> None:
    out = _results(tmp_path, {**ALL_OK, "lint": 1}, METRICS)
    summary = build_summary(out, "live", "20261105T101500Z", env=thresholds_env())
    assert summary["verdict"] == "FAIL"
    lint = [f for f in summary["failures"] if f["gate"] == "lint"]
    assert lint and lint[0]["expected"] == "exit code 0" and lint[0]["observed"] == "exit code 1"
    assert any(f["case_id"] == "N03" for f in summary["failures"])


def test_missing_gates_are_not_run_and_the_run_fails(tmp_path: Path) -> None:
    out = _results(tmp_path, {"integrity": 2}, None)
    summary = build_summary(out, "live", "20261105T101500Z", env=thresholds_env())
    statuses = {g["name"]: g["status"] for g in summary["gates"]}
    assert statuses["integrity"] == "FAIL" and statuses["lint"] == "NOT_RUN"
    assert summary["verdict"] == "FAIL"


def test_console_summary_has_layers_categories_aggregate_and_verdict(tmp_path: Path) -> None:
    out = _results(tmp_path, ALL_OK, METRICS)
    text = format_console(build_summary(out, "live", "20261105T101500Z", env=thresholds_env()))
    for needle in ("structural", "property", "semantic", "normal", "0.94", "PASS"):
        assert needle in text


def test_row_is_appended_to_the_end_and_nothing_else_changes(tmp_path: Path) -> None:
    log = tmp_path / "harness-log.md"
    log.write_text(LOG)
    out = _results(tmp_path, ALL_OK, METRICS)
    summary = build_summary(out, "live", "20261105T101500Z", env=thresholds_env())
    append_run_row(log, summary)
    append_run_row(log, summary)
    text = log.read_text()
    assert text.startswith(LOG)
    rows = [ln for ln in text.splitlines() if ln.startswith("| ") and "20261105T101500Z" in ln]
    assert len(rows) == 2 and rows[0].startswith("| 1 |") and rows[1].startswith("| 2 |")
    assert text.endswith("\n") and text.rstrip().splitlines()[-1] == rows[1]


def test_refuses_when_the_run_table_is_not_last(tmp_path: Path) -> None:
    log = tmp_path / "harness-log.md"
    log.write_text(LOG + "\n## 9. Appendix\n\ntext\n")
    out = _results(tmp_path, ALL_OK, METRICS)
    summary = build_summary(out, "live", "20261105T101500Z", env=thresholds_env())
    with pytest.raises(ValueError, match="run table"):
        append_run_row(log, summary)


def test_dry_run_writes_summary_but_not_the_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in thresholds_env().items():
        monkeypatch.setenv(key, value)
    log = tmp_path / "harness-log.md"
    log.write_text(LOG)
    out = _results(tmp_path, ALL_OK, METRICS)
    code = main(["--results-dir", str(out), "--mode", "live", "--log", str(log), "--dry-run"])
    assert code == 0
    assert log.read_text() == LOG
    assert json.loads((out / "summary.json").read_text())["verdict"] == "PASS"


def test_recorded_run_appends_a_row_and_returns_nonzero_on_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in thresholds_env().items():
        monkeypatch.setenv(key, value)
    log = tmp_path / "harness-log.md"
    log.write_text(LOG)
    out = _results(tmp_path, {**ALL_OK, "test": 1}, METRICS)
    code = main(["--results-dir", str(out), "--mode", "live", "--log", str(log)])
    assert code == 1
    assert "FAIL" in log.read_text().splitlines()[-1]
