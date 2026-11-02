"""Builds summary.json and the run-table row from a harness results folder.

Usage: summarize.py RESULTS_DIR
Writes RESULTS_DIR/summary.json and RESULTS_DIR/run-row.md, prints the row last, exits 1 on FAIL.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_coverage import backend_percentages, frontend_line_percent  # noqa: E402

GATES = ("integrity", "lint", "security", "test", "build", "e2e")
PYTEST_COMPARE = re.compile(r"^assert (.+?) == (.+)$")
VITEST_COMPARE = re.compile(r"^expected (.+?) to (?:be|equal|deeply equal) (.+?)(?: //.*)?$")


def gate_result(folder: Path, gate: str) -> dict[str, Any]:
    path = folder / f"{gate}.exitcode"
    if not path.exists():
        return {"exit_code": None, "status": "MISSING"}
    code = int(path.read_text(encoding="utf-8").strip())
    return {"exit_code": code, "status": "PASS" if code == 0 else "FAIL"}


def expected_observed(message: str) -> tuple[str | None, str | None]:
    """Return (expected, observed) when the first message line is a comparison."""
    first = message.strip().splitlines()[0] if message.strip() else ""
    if match := PYTEST_COMPARE.match(first):
        return match.group(2), match.group(1)
    if match := VITEST_COMPARE.match(first):
        return match.group(2), match.group(1)
    return None, None


def junit_failures(report: Path) -> list[dict[str, Any]]:
    suite = report.stem.removeprefix("junit-")
    root = ET.parse(report).getroot()  # noqa: S314 - reports are produced locally by pytest/vitest
    failures: list[dict[str, Any]] = []
    for case in root.iter("testcase"):
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        message = problem.get("message") or (problem.text or "")
        expected, observed = expected_observed(message)
        failures.append(
            {
                "gate": "test",
                "suite": suite,
                "test": f"{case.get('classname', '')}::{case.get('name', '')}",
                "expected": expected,
                "observed": observed,
                "message": message,
            }
        )
    return failures


def coverage_figures(folder: Path) -> dict[str, float | None]:
    figures: dict[str, float | None] = {
        "backend_line": None,
        "backend_branch": None,
        "frontend_line": None,
    }
    backend = folder / "coverage-backend.json"
    if backend.exists():
        figures["backend_line"], figures["backend_branch"] = (
            round(value, 1) for value in backend_percentages(backend)
        )
    frontend = folder / "coverage-frontend" / "coverage-summary.json"
    if frontend.exists():
        figures["frontend_line"] = round(frontend_line_percent(frontend), 1)
    return figures


def evidence_path(folder: Path) -> str:
    try:
        return str(folder.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(folder)


def main(argv: Sequence[str]) -> int:
    folder = Path(argv[0])
    gates = {gate: gate_result(folder, gate) for gate in GATES}
    failures: list[dict[str, Any]] = []
    for report in sorted(folder.glob("junit-*.xml")):
        failures.extend(junit_failures(report))

    result = "PASS" if all(item["status"] == "PASS" for item in gates.values()) else "FAIL"
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {
        "timestamp": timestamp,
        "result": result,
        "gates": gates,
        "failures": failures,
        "coverage": coverage_figures(folder),
    }
    (folder / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    cells = [timestamp, *(gates[gate]["status"] for gate in GATES), result, evidence_path(folder)]
    row = "| " + " | ".join(cells) + " |"
    (folder / "run-row.md").write_text(row + "\n", encoding="utf-8")
    print(f"Result: {result} ({len(failures)} failed tests)")
    print(row)
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
