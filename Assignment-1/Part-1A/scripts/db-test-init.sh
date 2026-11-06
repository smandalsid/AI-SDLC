#!/usr/bin/env bash
# Recreates <DB_NAME>_test from scratch, applies migrations, and loads the mock data.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
cd "$ROOT/src/backend"

DATABASE="$("$PY" -c 'from app.core.config import get_settings; print(get_settings().test_database_name)')"

"$PY" -m app.db.admin wait
"$PY" -m app.db.admin recreate --database "$DATABASE"
"$ROOT/.venv/bin/alembic" -x "database=$DATABASE" upgrade head
"$PY" -m app.db.seed --database "$DATABASE"
