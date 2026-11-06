"""Mask secrets in captured output (stdin filter) or scan a folder for them (--scan)."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from evaluators.common import JSON

MASK = "<redacted>"
SECRET_ENV_NAMES = ("GH_TOKEN", "COPILOT_GITHUB_TOKEN")
_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(?<=authorization: bearer )\S+"),
]


def secrets_from_env(env: Mapping[str, str]) -> list[str]:
    return [env[name] for name in SECRET_ENV_NAMES if env.get(name)]


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, MASK)
    for pattern in _PATTERNS:
        text = pattern.sub(MASK, text)
    return text


def redact_json(value: JSON, secrets: Iterable[str] = ()) -> JSON:
    if isinstance(value, str):
        return redact_text(value, secrets)
    if isinstance(value, list):
        return [redact_json(v, secrets) for v in value]
    if isinstance(value, dict):
        return {k: redact_json(v, secrets) for k, v in value.items()}
    return value


def find_secrets(text: str) -> list[str]:
    return [m.group(0) for p in _PATTERNS for m in p.finditer(text)]


def _scan(root: Path) -> int:
    files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    found = 0
    for path in files:
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if find_secrets(text):
            print(f"secret-like value in {path}")
            found += 1
    return 1 if found else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scan", type=Path, help="exit 1 if a secret-like value is found under PATH"
    )
    args = parser.parse_args(argv)
    if args.scan is not None:
        return _scan(args.scan)
    secrets = secrets_from_env(os.environ)
    sys.stdout.write(redact_text(sys.stdin.read(), secrets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
