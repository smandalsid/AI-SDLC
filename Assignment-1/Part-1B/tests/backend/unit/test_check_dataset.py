"""The dataset gate (MEC-1, MEC-2, MEC-3, FR-10)."""

import json

import pytest

from check_dataset import check_dataset
from harness_helpers import ROOT

pytestmark = pytest.mark.covers("FR-10", "AC-33")

SCHEMA = json.loads(
    (ROOT / "specs/001-nl-reminder-agent/contracts/eval-dataset.schema.json").read_text()
)
SPEC_IDS = {"AC-1", "FR-1"}
PREFIX = {
    "normal": "N",
    "boundary": "B",
    "ambiguous": "A",
    "missing_info": "M",
    "malformed": "X",
    "adversarial": "G",
}


def _case(category: str, number: int) -> dict[str, object]:
    return {
        "id": f"{PREFIX[category]}{number:02d}",
        "category": category,
        "input": {"text": "remind me"},
        "traces": ["AC-1"],
        "expected": {"intent": "create"},
    }


def _dataset() -> dict[str, object]:
    counts = {
        "normal": 3,
        "boundary": 3,
        "ambiguous": 3,
        "missing_info": 2,
        "malformed": 2,
        "adversarial": 2,
    }
    cases = [_case(cat, n) for cat, count in counts.items() for n in range(1, count + 1)]
    return {"version": 1, "cases": cases}


def _check(dataset: dict[str, object]) -> list[str]:
    return check_dataset(dataset, SCHEMA, SPEC_IDS, cases_min=15, category_min=2)


def test_a_valid_dataset_has_no_findings() -> None:
    assert _check(_dataset()) == []


def test_too_few_cases_is_reported() -> None:
    dataset = _dataset()
    dataset["cases"] = dataset["cases"][:14]  # type: ignore[index]  # JSON test
    assert any("fewer than 15" in f for f in _check(dataset))


def test_a_category_below_the_minimum_is_reported() -> None:
    dataset = _dataset()
    dataset["cases"] = [c for c in dataset["cases"] if c["id"] != "G02"]  # type: ignore[attr-defined]  # JSON test
    dataset["cases"].append(_case("normal", 4))  # type: ignore[attr-defined]  # JSON test
    assert any("adversarial" in f for f in _check(dataset))


def test_a_case_without_traces_is_reported() -> None:
    dataset = _dataset()
    del dataset["cases"][0]["traces"]  # type: ignore[index]  # JSON test
    assert any("traces" in f for f in _check(dataset))


def test_an_unknown_requirement_id_is_reported() -> None:
    dataset = _dataset()
    dataset["cases"][0]["traces"] = ["AC-999"]  # type: ignore[index]  # JSON test
    assert any("AC-999" in f for f in _check(dataset))


def test_duplicate_case_ids_are_reported() -> None:
    dataset = _dataset()
    dataset["cases"][1]["id"] = dataset["cases"][0]["id"]  # type: ignore[index]  # JSON test
    assert any("duplicate" in f for f in _check(dataset))


def test_a_schema_violation_is_reported() -> None:
    dataset = _dataset()
    dataset["cases"][0]["category"] = "other"  # type: ignore[index]  # JSON test
    assert _check(dataset)
