#!/usr/bin/env bash
# Gate 4: evaluation (layers 1 to 3 over evals/dataset.json) in MODE=live|replay.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.venv/bin:$PATH"
set -a
source .harness/config/thresholds.env
set +a
export PYTHONPATH="$PWD/src/backend:$PWD/.harness"

out="${HARNESS_OUT:-$(mktemp -d)}"
mkdir -p "$out"
args=(--mode "${MODE:-replay}" --results-dir "$out" --evidence-dir "${EVIDENCE_DIR:-evidence}")
if [ "${FINAL:-0}" = "1" ]; then
  args+=(--final)
fi
python .harness/eval_runner.py "${args[@]}"
