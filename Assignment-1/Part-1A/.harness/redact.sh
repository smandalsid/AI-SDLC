#!/usr/bin/env bash
# Replaces DB_PASSWORD, JWT_SECRET, and every MOCK_USER_PASSWORDS value from .env with <redacted> in piped output.
# REDACT_ENV_FILE overrides the file (tests).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export REDACT_ENV_FILE="${REDACT_ENV_FILE:-$ROOT/.env}"

exec "$ROOT/.venv/bin/python" -c '
import json
import os
import sys

secrets = []
try:
    with open(os.environ["REDACT_ENV_FILE"], encoding="utf-8") as handle:
        for line in handle:
            name, _, raw = line.partition("=")
            value = raw.strip().strip("\"\x27")
            if name in ("DB_PASSWORD", "JWT_SECRET"):
                secrets.append(value)
            elif name == "MOCK_USER_PASSWORDS":
                try:
                    parsed = json.loads(value)
                except ValueError:
                    continue
                if isinstance(parsed, dict):
                    secrets.extend(item for item in parsed.values() if isinstance(item, str))
except FileNotFoundError:
    pass

# Longest first so a password that contains a shorter one leaves no remainder.
secrets = sorted({item for item in secrets if item}, key=len, reverse=True)

for line in sys.stdin:
    for secret in secrets:
        line = line.replace(secret, "<redacted>")
    sys.stdout.write(line)
'
