#!/usr/bin/env bash
# Replaces the DB password from .env with <redacted> in piped output. REDACT_ENV_FILE overrides the file (tests).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export REDACT_ENV_FILE="${REDACT_ENV_FILE:-$ROOT/.env}"

exec "$ROOT/.venv/bin/python" -c '
import os
import sys

secret = ""
try:
    with open(os.environ["REDACT_ENV_FILE"], encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("DB_PASSWORD="):
                secret = line.split("=", 1)[1].strip().strip("\"\x27")
except FileNotFoundError:
    pass

for line in sys.stdin:
    sys.stdout.write(line.replace(secret, "<redacted>") if secret else line)
'
