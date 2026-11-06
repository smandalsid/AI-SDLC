"""Fail when a Python function is longer than FUNCTION_MAX_LINES lines (gate 1).

Usage: check_function_length.py [DIRECTORY]   (default: src/backend/app)
"""

import ast
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

DEFAULT_ROOT = Path("src/backend/app")


def find_long_functions(root: Path, limit: int) -> list[tuple[Path, int, str, int]]:
    """Return (file, first line, name, length) for every function longer than the limit."""
    found: list[tuple[Path, int, str, int]] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                if length > limit:
                    found.append((path, node.lineno, node.name, length))
    return found


def main(argv: Sequence[str], environ: Mapping[str, str]) -> int:
    raw_limit = environ.get("FUNCTION_MAX_LINES")
    if raw_limit is None or not raw_limit.isdigit():
        print("FUNCTION_MAX_LINES is not set; run through .harness/lint.sh", file=sys.stderr)
        return 2
    limit = int(raw_limit)
    root = Path(argv[0]) if argv else DEFAULT_ROOT

    violations = find_long_functions(root, limit)
    for path, line, name, length in violations:
        print(f"{path}:{line}: function '{name}' has {length} lines (limit {limit})")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
