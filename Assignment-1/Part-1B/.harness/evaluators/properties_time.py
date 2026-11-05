"""Layer 2: time and clarification properties (FR-1 to FR-4)."""

from __future__ import annotations

from evaluators.common import (
    JSON,
    CheckResult,
    Observation,
    action_of,
    case_now,
    case_zone,
    parse_instant,
    result,
    traced,
)

_TIMED = ("create", "reschedule")


def _timed_action(obs: Observation) -> JSON | None:
    action = action_of(obs)
    if action and action.get("intent") in _TIMED and action.get("datetime_iso"):
        return action
    return None


def _future(case: JSON, action: JSON, check_id: str, reqs: tuple[str, ...]) -> CheckResult:
    when = parse_instant(action["datetime_iso"])
    return result(
        "property", check_id, reqs, when > case_now(case), "after now", action["datetime_iso"]
    )


def check_fr1(case: JSON, obs: Observation) -> list[CheckResult]:
    if not traced(case, "FR-1"):
        return []
    reqs = ("FR-1",)
    out: list[CheckResult] = []
    action = _timed_action(obs)
    if action:
        when = parse_instant(action["datetime_iso"])
        local = when.astimezone(case_zone(case)).utcoffset()
        out.append(_future(case, action, "fr1.future", reqs))
        out.append(
            result(
                "property", "fr1.offset", reqs, when.utcoffset() == local, local, when.utcoffset()
            )
        )
    if case["expected"].get("intent") == "clarify":
        given = (action_of(obs) or {}).get("datetime_iso")
        out.append(result("property", "fr1.clarify_null", reqs, given is None, None, given))
    return out


def check_fr2(case: JSON, obs: Observation) -> list[CheckResult]:
    if not traced(case, "FR-2"):
        return []
    action = action_of(obs) or {}
    return [
        result(
            "property",
            f"fr2.null.{field}",
            ("FR-2",),
            action.get(field) is None,
            None,
            action.get(field),
        )
        for field in case["expected"].get("null_fields", [])
    ]


def check_fr3(case: JSON, obs: Observation) -> list[CheckResult]:
    if not traced(case, "FR-3"):
        return []
    reqs = ("FR-3",)
    expected = case["expected"]
    action = action_of(obs) or {}
    given = action.get("datetime_iso")
    if expected.get("intent") == "clarify":
        return [result("property", "fr3.no_datetime", reqs, given is None, None, given)]
    if expected.get("datetime_iso") and given:
        zone = case_zone(case)
        want = parse_instant(expected["datetime_iso"]).astimezone(zone).strftime("%H:%M")
        got = parse_instant(given).astimezone(zone).strftime("%H:%M")
        return [result("property", "fr3.clock", reqs, want == got, want, got)]
    return [result("property", "fr3.clock", reqs, False, expected.get("datetime_iso"), given)]


def check_fr4(case: JSON, obs: Observation) -> list[CheckResult]:
    if not traced(case, "FR-4"):
        return []
    reqs = ("FR-4",)
    out: list[CheckResult] = []
    action = _timed_action(obs)
    if action:
        out.append(_future(case, action, "fr4.future", reqs))
    if case["expected"].get("intent") == "clarify":
        given = (action_of(obs) or {}).get("datetime_iso")
        out.append(result("property", "fr4.no_datetime", reqs, given is None, None, given))
    return out
