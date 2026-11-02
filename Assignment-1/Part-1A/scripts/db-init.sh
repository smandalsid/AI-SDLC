#!/usr/bin/env bash
# Waits for the database, creates it if missing, applies migrations, and loads the mock data.
# Usage: scripts/db-init.sh [DATABASE_NAME]   (default: DB_NAME from .env)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
cd "$ROOT/src/backend"

DATABASE="${1:-$("$PY" -c 'from app.core.config import get_settings; print(get_settings().db_name)')}"

"$PY" -m app.db.admin wait
"$PY" -m app.db.admin create --database "$DATABASE"
"$ROOT/.venv/bin/alembic" -x "database=$DATABASE" upgrade head
"$PY" -m app.db.seed --database "$DATABASE"
