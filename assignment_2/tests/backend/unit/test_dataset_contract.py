"""The real evals/dataset.json (FR-10, AC-33)."""

import json
from collections import Counter
from datetime import datetime

import pytest

from check_dataset import check_dataset
from harness_helpers import ROOT, thresholds_env
from trace_report import parse_requirement_ids

pytestmark = pytest.mark.covers("FR-10", "AC-33", "FR-9")

DATASET = json.loads((ROOT / "evals/dataset.json").read_text())
CASES = DATASET["cases"]
SPEC = ROOT / "specs/001-nl-reminder-agent/spec.md"


def test_the_planned_33_cases_are_present_with_the_planned_ids() -> None:
    ids = {c["id"] for c in CASES}
    planned = (
        {f"N{n:02d}" for n in range(1, 11)}
        | {f"B{n:02d}" for n in range(1, 6)}
        | {f"A{n:02d}" for n in range(1, 5)}
        | {f"M{n:02d}" for n in range(1, 5)}
        | {f"X{n:02d}" for n in range(1, 5)}
        | {f"G{n:02d}" for n in range(1, 7)}
    )
    assert len(CASES) == 33 and ids == planned


def test_category_counts() -> None:
    counts = Counter(c["category"] for c in CASES)
    assert counts == {
        "normal": 10,
        "boundary": 5,
        "ambiguous": 4,
        "missing_info": 4,
        "malformed": 4,
        "adversarial": 6,
    }


def test_boundary_cases_cover_the_required_situations() -> None:
    boundary = {c["id"]: c for c in CASES if c["category"] == "boundary"}
    assert {"B01", "B02", "B03", "B04"} <= set(boundary)
    assert boundary["B03"]["input"]["timezone"] == "America/New_York"
    assert "AC-27" in boundary["B04"]["traces"] and "AC-24" in boundary["B01"]["traces"]


def test_exactly_the_eight_designated_cases_are_consistency_cases() -> None:
    flagged = {c["id"] for c in CASES if c.get("consistency")}
    assert flagged == {"N01", "N02", "N04", "N05", "N07", "N08", "N10", "B03"}


def test_every_case_has_an_aware_now_and_at_least_one_trace() -> None:
    for case in CASES:
        assert case["traces"], case["id"]
        now = case["input"].get("now")
        if case["category"] != "malformed":
            assert now and datetime.fromisoformat(now).tzinfo is not None, case["id"]


def test_the_dataset_passes_the_dataset_gate() -> None:
    schema = json.loads(
        (ROOT / "specs/001-nl-reminder-agent/contracts/eval-dataset.schema.json").read_text()
    )
    env = thresholds_env()
    ids = set(parse_requirement_ids(SPEC.read_text()))
    findings = check_dataset(
        DATASET, schema, ids, int(env["EVAL_CASES_MIN"]), int(env["EVAL_CATEGORY_MIN"])
    )
    assert findings == []
