"""Map every spec requirement to the tests and eval cases that cover it (MEC-24)."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

_DEFINITION = re.compile(r"\*\*((?:FR|INV|GR|AC)-\d+)\*\*")
Coverage = dict[str, set[str]]


def parse_requirement_ids(spec_text: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in _DEFINITION.finditer(spec_text):
        seen.setdefault(match.group(1))
    return list(seen)


def scan_test_markers(tests_dir: Path) -> Coverage:
    found: Coverage = {}
    for file in sorted(tests_dir.rglob("*.py")):
        for node in ast.walk(ast.parse(file.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "covers"
            ):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        found.setdefault(arg.value, set()).add(file.name)
    return found


def scan_dataset_traces(dataset: Path) -> Coverage:
    found: Coverage = {}
    for case in json.loads(dataset.read_text())["cases"]:
        for requirement in case["traces"]:
            found.setdefault(requirement, set()).add(case["id"])
    return found


def uncovered(
    ids: Sequence[str], tests: Mapping[str, set[str]], cases: Mapping[str, set[str]]
) -> list[str]:
    return [i for i in ids if not tests.get(i) and not cases.get(i)]


def render_table(
    ids: Sequence[str], tests: Mapping[str, set[str]], cases: Mapping[str, set[str]]
) -> str:
    rows = ["| Requirement | Tests | Eval cases |", "|-------------|-------|------------|"]
    for i in ids:
        tested = ", ".join(sorted(tests.get(i, ())))
        traced = ", ".join(sorted(cases.get(i, ())))
        rows.append(f"| {i} | {tested} | {traced} |")
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=Path("specs/001-nl-reminder-agent/spec.md"))
    parser.add_argument("--tests-dir", type=Path, default=Path("tests/backend"))
    parser.add_argument("--dataset", type=Path, default=Path("evals/dataset.json"))
    parser.add_argument("--check", action="store_true", help="exit 1 if any id is uncovered")
    args = parser.parse_args(argv)
    ids = parse_requirement_ids(args.spec.read_text())
    tests, cases = scan_test_markers(args.tests_dir), scan_dataset_traces(args.dataset)
    missing = uncovered(ids, tests, cases)
    if args.check:
        for i in missing:
            print(f"not covered by any test or eval case: {i}")
        return 1 if missing else 0
    print(render_table(ids, tests, cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
