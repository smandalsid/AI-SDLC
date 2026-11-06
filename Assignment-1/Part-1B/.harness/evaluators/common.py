"""Shared types and helpers for the three evaluator layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

JSON = Any  # parsed JSON has no static type


@dataclass(frozen=True)
class CheckResult:
    layer: str
    check_id: str
    requirement_ids: tuple[str, ...]
    passed: bool
    expected: str
    observed: str


@dataclass(frozen=True)
class Observation:
    """What one run of one case produced, as seen through the HTTP API."""

    status_code: int
    action: JSON | None
    applied: JSON | None
    model_calls: int
    infra_kind: str | None = None
    call: JSON | None = None


def traced(case: JSON, requirement_id: str) -> bool:
    return requirement_id in case["traces"]


def case_zone(case: JSON) -> ZoneInfo:
    return ZoneInfo(case["input"].get("timezone") or "UTC")


def case_now(case: JSON) -> datetime:
    return datetime.fromisoformat(case["input"]["now"])


def parse_instant(value: str) -> datetime:
    return datetime.fromisoformat(value)


def action_of(obs: Observation) -> JSON | None:
    """The action object when the call produced one, else None."""
    return obs.action if isinstance(obs.action, dict) else None


def result(
    layer: str,
    check_id: str,
    reqs: tuple[str, ...],
    passed: bool,
    expected: object,
    observed: object,
) -> CheckResult:
    return CheckResult(layer, check_id, reqs, passed, str(expected), str(observed))
