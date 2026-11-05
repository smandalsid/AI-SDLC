"""Every OpenAPI operation needs a success and a failure contract test; no unexplained skips."""

from __future__ import annotations

import argparse
import ast
import sys
import xml.etree.ElementTree as ET  # reads our own pytest junit output
from collections.abc import Sequence
from pathlib import Path

import yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
OUTCOMES = ("success", "failure")
VAGUE_SKIP_MESSAGES = {"", "unconditional skip", "xfail"}


def operations(openapi: Path) -> set[tuple[str, str]]:
    spec = yaml.safe_load(openapi.read_text())
    return {
        (method.upper(), path)
        for path, item in spec["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }


def marked_endpoints(tests_dir: Path) -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for file in tests_dir.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "endpoint"
            ):
                args = [a.value for a in node.args if isinstance(a, ast.Constant)]
                if len(args) == 3:
                    found.add((str(args[0]).upper(), str(args[1]), str(args[2])))
    return found


def missing_markers(openapi: Path, tests_dir: Path) -> list[str]:
    marked = marked_endpoints(tests_dir)
    return sorted(
        f"{method} {path} {outcome}"
        for method, path in operations(openapi)
        for outcome in OUTCOMES
        if (method, path, outcome) not in marked
    )


def skips_without_reason(junit: Path) -> list[str]:
    bad = []
    for case in ET.parse(junit).getroot().iter("testcase"):  # noqa: S314  # our own junit file
        skipped = case.find("skipped")
        if skipped is not None and (skipped.get("message") or "").strip() in VAGUE_SKIP_MESSAGES:
            bad.append(f"{case.get('classname')}::{case.get('name')}")
    return bad


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--openapi", type=Path, default=Path("specs/001-nl-reminder-agent/contracts/openapi.yaml")
    )
    parser.add_argument("--tests-dir", type=Path, default=Path("tests/backend/contract"))
    parser.add_argument("--junit", type=Path, default=None)
    args = parser.parse_args(argv)
    problems = [
        f"missing contract test: {m}" for m in missing_markers(args.openapi, args.tests_dir)
    ]
    if args.junit is not None and args.junit.exists():
        problems += [
            f"skip without a documented reason: {s}" for s in skips_without_reason(args.junit)
        ]
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
