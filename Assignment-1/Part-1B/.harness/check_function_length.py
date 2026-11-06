"""Fail when a function is longer than FUNC_LEN_MAX lines (MEC-9)."""

from __future__ import annotations

import argparse
import ast
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATHS = ("src/backend/app", ".harness")


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    name: str
    length: int


def find_long_functions(path: Path, limit: int) -> list[Violation]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > limit:
                found.append(Violation(str(path), node.lineno, node.name, length))
    return sorted(found, key=lambda v: v.line)


def _python_files(paths: Sequence[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files += sorted(f for f in p.rglob("*.py") if "__pycache__" not in f.parts)
        elif p.is_file():
            files.append(p)
    return files


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    limit = args.limit if args.limit is not None else int(os.environ["FUNC_LEN_MAX"])
    violations = [v for f in _python_files(args.paths) for v in find_long_functions(f, limit)]
    for v in violations:
        print(f"{v.path}:{v.line} {v.name} is {v.length} lines (limit {limit})")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
