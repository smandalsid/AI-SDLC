"""The wire model and domain model agree with the committed output schema (INV-1 to INV-8)."""

import json
from typing import Any

import pytest
from app_helpers import action_dict, create_dict
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.models.action import ProposedAction, ProposedActionWire
from harness_helpers import ROOT

pytestmark = pytest.mark.covers("INV-1", "INV-2", "INV-3", "INV-4", "INV-6", "INV-7", "INV-8")

SCHEMA = json.loads((ROOT / "evals" / "output-schema.json").read_text())


def _enum_values(prop: dict[str, Any]) -> set[Any]:
    if "enum" in prop:
        return set(prop["enum"])
    values: set[Any] = set()
    for branch in prop.get("anyOf", []):
        values |= {None} if branch.get("type") == "null" else _enum_values(branch)
    return values


def test_wire_properties_required_list_and_enums_match_the_schema() -> None:
    wire = ProposedActionWire.model_json_schema()
    assert set(wire["properties"]) == set(SCHEMA["properties"])
    assert set(wire["required"]) == set(SCHEMA["required"])
    assert wire["additionalProperties"] is False
    for name in ("intent", "refusal_reason"):
        assert _enum_values(wire["properties"][name]) - {None} == _enum_values(
            SCHEMA["properties"][name]
        ) - {None}


CASES = [
    action_dict(),
    create_dict(),
    create_dict(title=None),
    create_dict(datetime_iso="2026-11-09T09:00:00"),
    create_dict(title="x" * 121),
    action_dict(intent="delete"),
    action_dict(clarification_question=None),
    action_dict(clarification_question="x" * 201),
    create_dict(clarification_question="when?"),
    action_dict(intent="refuse", clarification_question=None),
    action_dict(intent="refuse", refusal_reason="injection", clarification_question=None),
    create_dict(refusal_reason="unsafe"),
    action_dict(intent="cancel", target_reminder_id="r1", clarification_question=None),
    action_dict(intent="cancel", clarification_question=None),
    action_dict(
        intent="snooze", target_reminder_id="r1", snooze_minutes=1441, clarification_question=None
    ),
    action_dict(
        intent="snooze", target_reminder_id="r1", snooze_minutes=1440, clarification_question=None
    ),
    action_dict(confidence=1.5),
    {**action_dict(), "extra": 1},
]


@pytest.mark.parametrize("data", CASES)
def test_schema_and_domain_model_accept_and_reject_the_same_actions(data: dict[str, Any]) -> None:
    by_schema = Draft202012Validator(SCHEMA).is_valid(data)
    try:
        ProposedAction.model_validate(data)
        by_model = True
    except ValidationError:
        by_model = False
    assert by_schema == by_model
