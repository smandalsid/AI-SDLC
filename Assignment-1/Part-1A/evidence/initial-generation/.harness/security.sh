#!/usr/bin/env bash
# Gate 2: SAST, dependency audit, secret scan. Runs every check; exits non-zero if any failed.
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

case "$SAST_FAIL_LEVEL" in
  low) BANDIT_LEVEL=-l ;;
  medium) BANDIT_LEVEL=-ll ;;
  high) BANDIT_LEVEL=-lll ;;
  *) echo "invalid SAST_FAIL_LEVEL: $SAST_FAIL_LEVEL"; exit 2 ;;
esac

check "bandit" "$BIN/bandit" -q -r src/backend/app "$BANDIT_LEVEL"
check "pip-audit" "$BIN/pip-audit" --local --progress-spinner off
check "npm audit" bash -c "cd src/frontend && npm audit --audit-level=$AUDIT_FAIL_LEVEL"
check "gitleaks dir" gitleaks dir . --config .harness/config/gitleaks.toml --no-banner --redact
check "gitleaks git" gitleaks git . --config .harness/config/gitleaks.toml --no-banner --redact

exit "$failed"
