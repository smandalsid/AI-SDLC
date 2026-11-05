#!/usr/bin/env bash
# The single entry point: integrity, lint, security, test, eval, then the summary and one run-table row.
#
#   .harness/run.sh [--mode live|replay] [--final] [--dry-run]
#
# Only a recorded run (no --dry-run) writes under evidence/ and appends to evidence/harness-log.md.
# --dry-run is not a run: it writes to a temporary folder and leaves the repository untouched.
# An integrity checksum mismatch (exit 2) aborts the remaining gates; any other failure continues.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.venv/bin:$PATH"
set -a
source .harness/config/thresholds.env
set +a

MODE=replay
DRY=0
FINAL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --final) FINAL=1; shift ;;
    *) echo "usage: run.sh [--mode live|replay] [--final] [--dry-run]" >&2; exit 64 ;;
  esac
done
case "$MODE" in live | replay) ;; *) echo "mode must be live or replay" >&2; exit 64 ;; esac

TS="$(date -u +%Y%m%dT%H%M%SZ)"
if [ "$DRY" = 1 ]; then
  OUT="$(mktemp -d)"
  export EVIDENCE_DIR="$OUT/evidence"
else
  OUT="evidence/harness-results/$TS"
  export EVIDENCE_DIR="evidence"
fi
mkdir -p "$OUT"
export HARNESS_OUT="$(cd "$OUT" && pwd)"
export MODE FINAL

for gate in integrity lint security test eval; do
  bash ".harness/$gate.sh" >"$HARNESS_OUT/$gate.stdout.raw" 2>"$HARNESS_OUT/$gate.stderr.raw"
  code=$?
  echo "$code" >"$HARNESS_OUT/$gate.exitcode"
  python .harness/redact.py <"$HARNESS_OUT/$gate.stdout.raw" >"$HARNESS_OUT/$gate.stdout"
  python .harness/redact.py <"$HARNESS_OUT/$gate.stderr.raw" >"$HARNESS_OUT/$gate.stderr"
  rm -f "$HARNESS_OUT/$gate.stdout.raw" "$HARNESS_OUT/$gate.stderr.raw"
  echo "gate $gate: exit $code"
  if [ "$gate" = integrity ] && [ "$code" = 2 ]; then
    echo "integrity checksum mismatch: remaining gates not run" >&2
    break
  fi
done

summary_args=(--results-dir "$OUT" --mode "$MODE" --log evidence/harness-log.md --timestamp "$TS")
[ "$DRY" = 1 ] && summary_args+=(--dry-run)
[ "$FINAL" = 1 ] && summary_args+=(--final)
python .harness/summarize.py "${summary_args[@]}"
