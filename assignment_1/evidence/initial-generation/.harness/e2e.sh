#!/usr/bin/env bash
# Gate 5: Playwright end-to-end checks. Playwright's webServer starts the backend (scripts/e2e-backend.sh)
# and the frontend; this script only checks that the database accepts connections.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

env_value() {
  # Reads one non-secret variable from .env without sourcing the file.
  grep -E "^$1=" .env 2>/dev/null | head -n1 | cut -d= -f2- || true
}

DB_HOST="$(env_value DB_HOST)"
DB_PORT="$(env_value DB_PORT)"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-1433}"

if ! bash -c "echo > /dev/tcp/$DB_HOST/$DB_PORT" 2>/dev/null; then
  echo "database is not reachable on $DB_HOST:$DB_PORT; start it with scripts/dev.sh or docker start azure-sql-edge"
  exit 1
fi

cd src/frontend && npx playwright test
