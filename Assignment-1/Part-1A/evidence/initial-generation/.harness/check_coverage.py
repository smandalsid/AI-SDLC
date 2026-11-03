"""Coverage thresholds and skipped-test rule for the test gate (gate 3).

Usage: check_coverage.py RESULTS_DIR   (thresholds come from the environment, set by test.sh)
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path


def backend_percentages(path: Path) -> tuple[float, float]:
    """Return (line %, branch %) from coverage.py's JSON report."""
    totals = json.loads(path.read_text(encoding="utf-8"))["totals"]
    statements = totals.get("num_statements", 0)
    branches = totals.get("num_branches", 0)
    line = 100.0 if statements == 0 else 100.0 * totals["covered_lines"] / statements
    branch = 100.0 if branches == 0 else 100.0 * totals["covered_branches"] / branches
    return line, branch


def frontend_line_percent(path: Path) -> float:
    summary = json.loads(path.read_text(encoding="utf-8"))
    pct = summary["total"]["lines"]["pct"]
    # Vitest reports the string "Unknown" when no source file was covered.
    return float(pct) if isinstance(pct, int | float) else 0.0


def count_skipped(junit: Path) -> int:
    """Count skipped and xfail test cases in a junit report."""
    root = ET.parse(junit).getroot()  # noqa: S314 - reports are produced locally by pytest/vitest
    return len(root.findall(".//skipped"))


def check_threshold(label: str, actual: float, minimum: float) -> bool:
    ok = actual >= minimum
    print(f"{label}: {actual:.1f}% (minimum {minimum:g}%) {'PASS' if ok else 'FAIL'}")
    return ok


def main(argv: Sequence[str], environ: Mapping[str, str]) -> int:
    folder = Path(argv[0])
    try:
        line_min = float(environ["BACKEND_COVERAGE_LINE_MIN"])
        branch_min = float(environ["BACKEND_COVERAGE_BRANCH_MIN"])
        frontend_min = float(environ["FRONTEND_COVERAGE_LINE_MIN"])
    except KeyError as error:
        print(f"threshold {error} is not set; run through .harness/test.sh", file=sys.stderr)
        return 2

    ok = True
    try:
        line, branch = backend_percentages(folder / "coverage-backend.json")
        ok &= check_threshold("backend line coverage", line, line_min)
        ok &= check_threshold("backend branch coverage", branch, branch_min)
        frontend = frontend_line_percent(folder / "coverage-frontend" / "coverage-summary.json")
        ok &= check_threshold("frontend line coverage", frontend, frontend_min)
    except FileNotFoundError as error:
        print(f"missing coverage report: {error.filename}")
        ok = False

    for report in sorted(folder.glob("junit-*.xml")):
        skipped = count_skipped(report)
        print(f"{report.name}: {skipped} skipped or xfail tests {'FAIL' if skipped else 'PASS'}")
        ok &= skipped == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
