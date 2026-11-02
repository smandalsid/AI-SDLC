#!/usr/bin/env bash
# Gate 3: pytest and vitest with coverage; thresholds and skipped-test rules checked by check_coverage.py.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source .harness/config/thresholds.env
set +a

HARNESS_OUT="${HARNESS_OUT:-$(mktemp -d)}"
mkdir -p "$HARNESS_OUT"
echo "results folder: $HARNESS_OUT"
failed=0

echo "== pytest"
(cd src/backend && "$ROOT/.venv/bin/pytest" --cov --cov-branch \
  --cov-report="json:$HARNESS_OUT/coverage-backend.json" \
  --junitxml="$HARNESS_OUT/junit-backend.xml") || failed=1

echo "== vitest"
(cd src/frontend && npx vitest run --coverage \
  --coverage.reporter=text --coverage.reporter=json-summary \
  --coverage.reportsDirectory="$HARNESS_OUT/coverage-frontend" \
  --reporter=default --reporter=junit --outputFile.junit="$HARNESS_OUT/junit-frontend.xml") || failed=1

echo "== coverage thresholds and skipped tests"
.venv/bin/python .harness/check_coverage.py "$HARNESS_OUT" || failed=1

exit "$failed"
