#!/usr/bin/env bash
# Gate 0: integrity and scope. The checksum comparison runs first and aborts the whole run on a mismatch.
#
# A legitimate change to a protected file (scripts, thresholds, dataset, output schema, lint/type/secret-scan
# configuration) needs an approved spec revision. Afterwards a human runs .harness/regen_checksums.sh and
# reviews the checksum diff. The agent never regenerates the checksums after the Foundational approval.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.venv/bin:$PATH"
set -a
source .harness/config/thresholds.env
set +a

if ! shasum -a 256 -c .harness/config/checksums.sha256 --quiet; then
  echo "INTEGRITY FAILURE: a protected file does not match .harness/config/checksums.sha256" >&2
  exit 2
fi

rc=0
if [ "$(git branch --show-current)" = "main" ]; then
  echo "branch check failed: work must not happen on main" >&2
  rc=1
fi

prefix="$(git rev-parse --show-prefix)"
outside="$(git diff --name-only main...HEAD | grep -v "^${prefix}" || true)"
if [ -n "$outside" ]; then
  echo "scope check failed: paths changed outside ${prefix}:" >&2
  echo "$outside" >&2
  rc=1
fi

python .harness/check_dataset.py || rc=1
exit "$rc"
