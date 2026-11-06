"""Requirement-to-test and eval-case traceability (MEC-24)."""

import json
from pathlib import Path

import pytest

from trace_report import (
    main,
    parse_requirement_ids,
    render_table,
    scan_dataset_traces,
    scan_test_markers,
    uncovered,
)

pytestmark = pytest.mark.covers("MEC-24")

SPEC = """- **FR-1**: a
- **INV-2**: b
- **AC-3** (FR-1): c
- **GR-4**: d
Mentions of FR-9 in prose are not definitions.
"""

TESTS = """import pytest

pytestmark = pytest.mark.covers("FR-1", "INV-2")

@pytest.mark.covers("AC-3")
def test_a() -> None: ...
"""


def _files(tmp_path: Path) -> tuple[Path, Path, Path]:
    spec = tmp_path / "spec.md"
    spec.write_text(SPEC)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_a.py").write_text(TESTS)
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps({"cases": [{"id": "N01", "traces": ["GR-4", "FR-1"]}]}))
    return spec, tests_dir, dataset


def test_requirement_ids_come_from_the_bold_definitions_only() -> None:
    assert parse_requirement_ids(SPEC) == ["FR-1", "INV-2", "AC-3", "GR-4"]


def test_markers_and_dataset_traces_are_collected(tmp_path: Path) -> None:
    _, tests_dir, dataset = _files(tmp_path)
    tests = scan_test_markers(tests_dir)
    assert tests["FR-1"] == {"test_a.py"} and tests["AC-3"] == {"test_a.py"}
    assert scan_dataset_traces(dataset) == {"GR-4": {"N01"}, "FR-1": {"N01"}}


def test_an_id_covered_by_nothing_is_reported(tmp_path: Path) -> None:
    spec, tests_dir, dataset = _files(tmp_path)
    ids = parse_requirement_ids(spec.read_text())
    assert uncovered(ids, scan_test_markers(tests_dir), scan_dataset_traces(dataset)) == []
    assert uncovered(
        [*ids, "FR-9"], scan_test_markers(tests_dir), scan_dataset_traces(dataset)
    ) == ["FR-9"]


def test_table_lists_tests_and_cases(tmp_path: Path) -> None:
    spec, tests_dir, dataset = _files(tmp_path)
    table = render_table(
        parse_requirement_ids(spec.read_text()),
        scan_test_markers(tests_dir),
        scan_dataset_traces(dataset),
    )
    assert "| FR-1 | test_a.py | N01 |" in table and "| Requirement |" in table


def test_check_exits_nonzero_and_names_the_uncovered_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    spec, tests_dir, dataset = _files(tmp_path)
    args = [
        "--check",
        "--spec",
        str(spec),
        "--tests-dir",
        str(tests_dir),
        "--dataset",
        str(dataset),
    ]
    assert main(args) == 0
    spec.write_text(SPEC + "- **FR-9**: e\n")
    assert main(args) == 1
    assert "FR-9" in capsys.readouterr().out
