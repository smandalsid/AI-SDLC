"""Coverage thresholds read from a coverage.py JSON report (MEC-7, MEC-8)."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from evaluators.common import JSON


def check_coverage(totals: JSON, line_min: float, branch_min: float) -> list[str]:
    statements = totals["num_statements"]
    if statements == 0:
        return ["no coverage data: zero statements"]
    findings: list[str] = []
    line = 100.0 * totals["covered_lines"] / statements
    if line < line_min:
        findings.append(f"line coverage {line:.1f}% is below {line_min}%")
    branches = totals["num_branches"]
    branch = 100.0 * totals["covered_branches"] / branches if branches else 100.0
    if branch < branch_min:
        findings.append(f"branch coverage {branch:.1f}% is below {branch_min}%")
    return findings


def main(argv: Sequence[str]) -> int:
    report = Path(argv[0])
    if not report.exists():
        print(f"coverage report missing: {report}")
        return 1
    totals = json.loads(report.read_text())["totals"]
    findings = check_coverage(
        totals, float(os.environ["LINE_COVERAGE_MIN"]), float(os.environ["BRANCH_COVERAGE_MIN"])
    )
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
