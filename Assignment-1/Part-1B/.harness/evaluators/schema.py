"""Layer 1: structural validation against the committed output schema (INV-1 to INV-8)."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from evaluators.common import JSON, CheckResult, Observation, result

DEFAULT_SCHEMA = Path(__file__).resolve().parents[2] / "evals" / "output-schema.json"

_PATH_TO_INV = {
    "intent": "INV-2",
    "title": "INV-1",
    "datetime_iso": "INV-3",
    "snooze_minutes": "INV-4",
    "target_reminder_id": "INV-5",
    "clarification_question": "INV-6",
    "refusal_reason": "INV-7",
    "confidence": "INV-1",
}
_INVARIANTS = tuple(f"INV-{n}" for n in range(1, 9))


def load_schema(path: Path = DEFAULT_SCHEMA) -> JSON:
    return json.loads(path.read_text())


def _classify(error: JSON) -> str:
    if error.validator == "additionalProperties":
        return "INV-8"
    if error.absolute_path:
        return _PATH_TO_INV.get(str(error.absolute_path[0]), "INV-1")
    return "INV-1"


def _violated(action: JSON, case: JSON, schema: JSON) -> set[str]:
    if not isinstance(action, dict):
        return set(_INVARIANTS)
    violated = {_classify(e) for e in Draft202012Validator(schema).iter_errors(action)}
    if violated:
        violated.add("INV-1")
    supplied = {r["id"] for r in case["input"].get("reminders", [])}
    target = action.get("target_reminder_id")
    if target is not None and target not in supplied:
        violated.add("INV-5")
    return violated


def run_structural(case: JSON, obs: Observation, schema: JSON) -> list[CheckResult]:
    if obs.action is None:
        if "http_status" in case["expected"]:
            return []
        return [
            result("structural", "inv1", ("INV-1",), False, "an action", f"HTTP {obs.status_code}")
        ]
    violated = _violated(obs.action, case, schema)
    return [
        result(
            "structural",
            f"inv{n}",
            (f"INV-{n}",),
            f"INV-{n}" not in violated,
            "valid",
            "valid" if f"INV-{n}" not in violated else "violated",
        )
        for n in range(1, 9)
    ]
