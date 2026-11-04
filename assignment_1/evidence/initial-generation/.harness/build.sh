#!/usr/bin/env bash
# Gate 4: production build and initial-JS size budget.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source .harness/config/thresholds.env
set +a

echo "== vite build"
(cd src/frontend && npx vite build) || exit 1

echo "== bundle size"
node .harness/check_bundle_size.mjs
