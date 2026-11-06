#!/usr/bin/env bash
# Resets the e2e test database (<DB_NAME>_test) to the seeded state; used by the Playwright specs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/src/backend"

DATABASE="$("$ROOT/.venv/bin/python" -c 'from app.core.config import get_settings; print(get_settings().test_database_name)')"
exec "$ROOT/.venv/bin/python" -m app.db.seed --database "$DATABASE"
