#!/usr/bin/env bash
# Regenerate .harness/config/checksums.sha256 over every protected file.
# After the Foundational approval only a human runs this, after an approved spec revision, and reviews the diff.
set -euo pipefail
cd "$(dirname "$0")/.."

files=(
  .harness/*.sh
  .harness/*.py
  .harness/evaluators/*.py
  .harness/config/thresholds.env
  .harness/config/ruff.toml
  .harness/config/mypy.ini
  .harness/config/gitleaks.toml
  .harness/config/bandit.yaml
  evals/dataset.json
  evals/output-schema.json
)
shasum -a 256 "${files[@]}" >.harness/config/checksums.sha256
echo "wrote $(wc -l <.harness/config/checksums.sha256 | tr -d ' ') checksums"
