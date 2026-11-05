#!/usr/bin/env bash
# Gate 3: unit and contract tests with coverage, endpoint-test and traceability checks.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.venv/bin:$PATH"
set -a
source .harness/config/thresholds.env
set +a

out="${HARNESS_OUT:-$(mktemp -d)}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"

rc=0
(cd src/backend && pytest -q --cov=app --cov-branch --cov-report="json:$out/coverage.json" --junitxml="$out/junit.xml") || rc=1
python .harness/check_coverage.py "$out/coverage.json" || rc=1
python .harness/check_endpoint_tests.py --junit "$out/junit.xml" || rc=1
python .harness/trace_report.py --check || rc=1
exit "$rc"
