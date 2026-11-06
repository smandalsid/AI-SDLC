"""The dataset gate: size, categories, traceability and schema (MEC-1, MEC-2, MEC-3)."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from collections.abc import Collection, Sequence
from pathlib import Path

from jsonschema import Draft202012Validator

from evaluators.common import JSON
from trace_report import parse_requirement_ids

DEFAULT_DATASET = "evals/dataset.json"
DEFAULT_SCHEMA = "specs/001-nl-reminder-agent/contracts/eval-dataset.schema.json"
DEFAULT_SPEC = "specs/001-nl-reminder-agent/spec.md"
CATEGORIES = ("normal", "boundary", "ambiguous", "missing_info", "malformed", "adversarial")


def _case_findings(cases: list[JSON], spec_ids: Collection[str]) -> list[str]:
    findings: list[str] = []
    ids = Counter(c.get("id") for c in cases)
    findings += [f"duplicate case id {i}" for i, n in ids.items() if n > 1]
    for case in cases:
        if not case.get("traces"):
            findings.append(f"case {case.get('id')} has no traces")
        findings += [
            f"case {case.get('id')} traces unknown requirement {t}"
            for t in case.get("traces", [])
            if t not in spec_ids
        ]
    return findings


def check_dataset(
    dataset: JSON, schema: JSON, spec_ids: Collection[str], cases_min: int, category_min: int
) -> list[str]:
    findings = [f"schema: {e.message}" for e in Draft202012Validator(schema).iter_errors(dataset)]
    cases = [c for c in dataset.get("cases", []) if isinstance(c, dict)]
    if len(cases) < cases_min:
        findings.append(f"fewer than {cases_min} cases ({len(cases)})")
    counts = Counter(c.get("category") for c in cases)
    findings += [
        f"category {cat} has {counts.get(cat, 0)} cases, minimum {category_min}"
        for cat in CATEGORIES
        if counts.get(cat, 0) < category_min
    ]
    return findings + _case_findings(cases, spec_ids)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    dataset = json.loads(Path(DEFAULT_DATASET).read_text())
    schema = json.loads(Path(DEFAULT_SCHEMA).read_text())
    spec_ids = parse_requirement_ids(Path(DEFAULT_SPEC).read_text())
    findings = check_dataset(
        dataset,
        schema,
        spec_ids,
        int(os.environ["EVAL_CASES_MIN"]),
        int(os.environ["EVAL_CATEGORY_MIN"]),
    )
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
