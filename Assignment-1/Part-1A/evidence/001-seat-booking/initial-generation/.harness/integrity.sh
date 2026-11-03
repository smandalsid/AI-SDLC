#!/usr/bin/env bash
# Gate 0: harness scripts, thresholds, and lint/type/secret-scan configuration are unchanged.
#
# After a legitimate, reviewed change to a protected file, regenerate the checksums from the repository root:
#   shasum -a 256 .harness/*.sh .harness/*.py .harness/*.mjs .harness/config/thresholds.env \
#     .harness/config/gitleaks.toml src/backend/ruff.toml src/backend/mypy.ini \
#     src/frontend/eslint.config.js src/frontend/tsconfig.json > .harness/config/checksums.sha256
# The regenerated file must be committed so the change is visible in review (constitution XII).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
shasum -a 256 -c .harness/config/checksums.sha256
