#!/usr/bin/env bash
# Gate 1: syntax, lint, types, function length. Runs every check and fails if any failed.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.venv/bin:$PATH"
set -a
source .harness/config/thresholds.env
set +a

targets=(src/backend/app tests/backend .harness/*.py .harness/evaluators/*.py)
rc=0
ruff check --config .harness/config/ruff.toml --config "lint.mccabe.max-complexity = ${COMPLEXITY_MAX}" "${targets[@]}" || rc=1
ruff format --check --config .harness/config/ruff.toml "${targets[@]}" || rc=1
mypy --config-file .harness/config/mypy.ini "${targets[@]}" || rc=1
python .harness/check_function_length.py || rc=1
exit "$rc"
