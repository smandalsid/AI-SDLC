#!/usr/bin/env bash
# Gate 1: syntax, lint, types, complexity, function length. Runs every check; exits non-zero if any failed.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source .harness/config/thresholds.env
set +a

BIN=.venv/bin
failed=0
check() {
  local name="$1"
  shift
  echo "== $name"
  if "$@"; then echo "-- $name: PASS"; else echo "-- $name: FAIL"; failed=1; fi
}

check "ruff check" "$BIN/ruff" check --config src/backend/ruff.toml \
  --config "lint.mccabe.max-complexity=$COMPLEXITY_MAX" src/backend tests/backend
check "ruff format" "$BIN/ruff" format --check --config src/backend/ruff.toml src/backend tests/backend
check "mypy" "$BIN/mypy" --config-file src/backend/mypy.ini src/backend/app tests/backend
check "function length" "$BIN/python" .harness/check_function_length.py
check "eslint" bash -c 'cd src/frontend && npx eslint . --max-warnings 0'
check "tsc" bash -c 'cd src/frontend && npx tsc --noEmit'

exit "$failed"
