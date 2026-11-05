"""Coverage thresholds read from coverage.py JSON (MEC-7, MEC-8)."""

import json
from pathlib import Path

import pytest

from check_coverage import check_coverage, main
from harness_helpers import thresholds_env

pytestmark = pytest.mark.covers("MEC-7", "MEC-8")


def _totals(lines: int, statements: int, branches: int, num_branches: int) -> dict[str, object]:
    return {
        "covered_lines": lines,
        "num_statements": statements,
        "covered_branches": branches,
        "num_branches": num_branches,
    }


def test_exactly_at_the_minimums_passes() -> None:
    assert check_coverage(_totals(85, 100, 16, 20), 85.0, 80.0) == []


def test_below_either_minimum_fails_and_names_it() -> None:
    assert any("line" in f for f in check_coverage(_totals(84, 100, 16, 20), 85.0, 80.0))
    assert any("branch" in f for f in check_coverage(_totals(90, 100, 15, 20), 85.0, 80.0))


def test_zero_statements_is_a_failure_never_a_pass() -> None:
    assert check_coverage(_totals(0, 0, 0, 0), 85.0, 80.0) == ["no coverage data: zero statements"]


def test_a_missing_report_is_a_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "absent.json")]) == 1
    assert "coverage report missing" in capsys.readouterr().out


def test_main_reads_thresholds_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in thresholds_env().items():
        monkeypatch.setenv(key, value)
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"totals": _totals(90, 100, 18, 20)}))
    assert main([str(report)]) == 0
    report.write_text(json.dumps({"totals": _totals(10, 100, 1, 20)}))
    assert main([str(report)]) == 1
