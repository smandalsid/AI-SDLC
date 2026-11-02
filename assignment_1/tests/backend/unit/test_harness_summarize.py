import json
from pathlib import Path

import pytest

from .harness_loader import load_harness_module

GATES = ("integrity", "lint", "security", "test", "build", "e2e")

BACKEND_JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="2" failures="1">
<testcase classname="tests.backend.contract.test_buses" name="test_detail_has_20_seats" time="0.1">
<failure message="assert 404 == 200">assert 404 == 200 + where 404 = response.status_code</failure>
</testcase>
<testcase classname="tests.backend.contract.test_buses" name="test_list" time="0.1"/>
</testsuite></testsuites>
"""

FRONTEND_JUNIT = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites><testsuite name="vitest" tests="1" failures="1">
<testcase classname="tests/components/SeatGrid.test.tsx" name="booked seats are disabled">
<failure message="expected 'booked' to be 'available'" type="AssertionError">trace</failure>
</testcase>
</testsuite></testsuites>
"""


def make_results(folder: Path, exit_codes: dict[str, int], with_failures: bool) -> None:
    for gate in GATES:
        (folder / f"{gate}.exitcode").write_text(f"{exit_codes.get(gate, 0)}\n", encoding="utf-8")
    backend_xml = (
        BACKEND_JUNIT
        if with_failures
        else '<testsuites><testsuite name="pytest" tests="1"/></testsuites>'
    )
    frontend_xml = (
        FRONTEND_JUNIT
        if with_failures
        else '<testsuites><testsuite name="vitest" tests="1"/></testsuites>'
    )
    (folder / "junit-backend.xml").write_text(backend_xml, encoding="utf-8")
    (folder / "junit-frontend.xml").write_text(frontend_xml, encoding="utf-8")
    (folder / "coverage-backend.json").write_text(
        json.dumps(
            {
                "totals": {
                    "covered_lines": 90,
                    "num_statements": 100,
                    "covered_branches": 40,
                    "num_branches": 50,
                }
            }
        ),
        encoding="utf-8",
    )
    (folder / "coverage-frontend").mkdir()
    (folder / "coverage-frontend" / "coverage-summary.json").write_text(
        json.dumps({"total": {"lines": {"pct": 85.5}}}), encoding="utf-8"
    )


def run_summarize(
    folder: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, object], list[str]]:
    module = load_harness_module("summarize")
    code: int = module.main([str(folder)])
    row = [cell.strip() for cell in capsys.readouterr().out.strip().splitlines()[-1].split("|")]
    summary: dict[str, object] = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    return code, summary, row


def test_failed_run_lists_each_failed_test_with_expected_and_observed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    make_results(tmp_path, {"test": 1}, with_failures=True)

    code, summary, row = run_summarize(tmp_path, capsys)

    assert code == 1
    assert summary["result"] == "FAIL"
    failures = summary["failures"]
    assert isinstance(failures, list)
    by_test = {failure["test"]: failure for failure in failures}
    backend = by_test["tests.backend.contract.test_buses::test_detail_has_20_seats"]
    assert (backend["gate"], backend["expected"], backend["observed"]) == ("test", "200", "404")
    frontend = by_test["tests/components/SeatGrid.test.tsx::booked seats are disabled"]
    assert (frontend["expected"], frontend["observed"]) == ("'available'", "'booked'")


def test_run_table_row_has_a_status_per_gate_in_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    make_results(tmp_path, {"test": 1}, with_failures=True)

    _, summary, row = run_summarize(tmp_path, capsys)

    # Columns: '', timestamp, integrity, lint, security, tests, build, e2e, result, evidence, ''
    assert row[2:9] == ["PASS", "PASS", "PASS", "FAIL", "PASS", "PASS", "FAIL"]
    gates = summary["gates"]
    assert isinstance(gates, dict)
    assert gates["test"]["exit_code"] == 1
    assert gates["lint"]["status"] == "PASS"


def test_coverage_figures_are_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    make_results(tmp_path, {}, with_failures=False)

    _, summary, _ = run_summarize(tmp_path, capsys)

    assert summary["coverage"] == {
        "backend_line": 90.0,
        "backend_branch": 80.0,
        "frontend_line": 85.5,
    }


def test_all_green_run_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    make_results(tmp_path, {}, with_failures=False)

    code, summary, row = run_summarize(tmp_path, capsys)

    assert code == 0
    assert summary["result"] == "PASS"
    assert summary["failures"] == []
    assert row[8] == "PASS"


def test_missing_gate_result_counts_as_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    make_results(tmp_path, {}, with_failures=False)
    (tmp_path / "build.exitcode").unlink()

    code, summary, row = run_summarize(tmp_path, capsys)

    assert code == 1
    assert summary["result"] == "FAIL"
    assert row[6] == "MISSING"
