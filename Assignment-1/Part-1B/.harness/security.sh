#!/usr/bin/env bash
# Gate 2: security. Runs every check and fails if any failed.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.venv/bin:$PATH"

rc=0
bandit -ll -c .harness/config/bandit.yaml -r src/backend/app || rc=1
# If the package index is unreachable through a proxy, report the blocker; never skip or relax this check.
pip-audit || rc=1
gitleaks dir . --config .harness/config/gitleaks.toml --no-banner || rc=1
gitleaks git --staged --config .harness/config/gitleaks.toml --no-banner . || rc=1
python .harness/redact.py --scan evidence || rc=1
exit "$rc"
