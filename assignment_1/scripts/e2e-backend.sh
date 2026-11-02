#!/usr/bin/env bash
# Starts the backend on the test database; used by the Playwright webServer (src/frontend/playwright.config.ts).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/scripts/db-test-init.sh"

cd "$ROOT/src/backend"
DB_NAME="$("$ROOT/.venv/bin/python" -c 'from app.core.config import get_settings; print(get_settings().test_database_name)')"
export DB_NAME
exec "$ROOT/.venv/bin/uvicorn" app.main:create_app --factory --host 127.0.0.1 --port 8000
