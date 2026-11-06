#!/usr/bin/env bash
# Runs every gate in order, continues after a failure, and records evidence.
#   .harness/run.sh            recorded run: evidence/harness-results/<timestamp>/ plus a row in harness-log.md
#   .harness/run.sh --dry-run  same gates into a temporary folder; evidence/ and harness-log.md are untouched
# Only recorded runs count as evidence (constitution XII); the first one happens after the initial-generation snapshot.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ "$DRY_RUN" == 1 ]]; then
  HARNESS_OUT="$(mktemp -d)"
else
  HARNESS_OUT="$ROOT/evidence/harness-results/$STAMP"
  mkdir -p "$HARNESS_OUT"
fi
export HARNESS_OUT
RAW="$(mktemp -d)"
trap 'rm -rf "$RAW"' EXIT

for gate in integrity lint security test build e2e; do
  echo "[harness] gate: $gate"
  bash ".harness/$gate.sh" >"$RAW/$gate.out" 2>"$RAW/$gate.err"
  code=$?
  .harness/redact.sh <"$RAW/$gate.out" >"$HARNESS_OUT/$gate.stdout"
  .harness/redact.sh <"$RAW/$gate.err" >"$HARNESS_OUT/$gate.stderr"
  echo "$code" >"$HARNESS_OUT/$gate.exitcode"
  echo "[harness] gate: $gate exit code $code"
done

redact_in_place() {
  local file="$1"
  .harness/redact.sh <"$file" >"$RAW/redacted.tmp" && mv "$RAW/redacted.tmp" "$file"
}
for file in "$HARNESS_OUT"/*.xml "$HARNESS_OUT"/*.json; do
  [[ -f "$file" ]] && redact_in_place "$file"
done

.venv/bin/python .harness/summarize.py "$HARNESS_OUT"
summary_code=$?
[[ -f "$HARNESS_OUT/summary.json" ]] && redact_in_place "$HARNESS_OUT/summary.json"

if [[ "$DRY_RUN" == 0 ]]; then
  # The run table is the last section of the log; append the row at the very end.
  cat "$HARNESS_OUT/run-row.md" >>evidence/harness-log.md
  echo "[harness] recorded in $HARNESS_OUT and evidence/harness-log.md"
else
  echo "[harness] dry run: nothing recorded (results in $HARNESS_OUT)"
fi

if [[ "$summary_code" == 0 ]]; then echo "HARNESS RESULT: PASS"; else echo "HARNESS RESULT: FAIL"; fi
exit "$summary_code"
