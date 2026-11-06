"""Layer 2: targets, applied results, input handling and consistency (FR-5 to FR-9)."""

from __future__ import annotations

from evaluators.common import (
    JSON,
    CheckResult,
    Observation,
    action_of,
    parse_instant,
    result,
    traced,
)

MAX_TEXT = 1000


def check_fr5(case: JSON, obs: Observation) -> list[CheckResult]:
    if not traced(case, "FR-5") or "target_reminder_id" not in case["expected"]:
        return []
    reqs = ("FR-5",)
    target = (action_of(obs) or {}).get("target_reminder_id")
    want = case["expected"]["target_reminder_id"]
    out = [result("property", "fr5.target", reqs, target == want, want, target)]
    if target is not None:
        supplied = {r["id"] for r in case["input"].get("reminders", [])}
        out.append(
            result("property", "fr5.in_list", reqs, target in supplied, sorted(supplied), target)
        )
    return out


def check_fr6(case: JSON, obs: Observation) -> list[CheckResult]:
    expected = case["expected"]
    if not traced(case, "FR-6") or "applied_time" not in expected:
        return []
    reqs = ("FR-6",)
    new_time = (obs.applied or {}).get("new_time")
    same = new_time is not None and parse_instant(new_time) == parse_instant(
        expected["applied_time"]
    )
    out = [result("property", "fr6.new_time", reqs, same, expected["applied_time"], new_time)]
    if "snooze_minutes" in expected:
        minutes = (action_of(obs) or {}).get("snooze_minutes")
        out.append(
            result(
                "property",
                "fr6.minutes",
                reqs,
                minutes == expected["snooze_minutes"],
                expected["snooze_minutes"],
                minutes,
            )
        )
    return out


def check_fr7(case: JSON, obs: Observation) -> list[CheckResult]:
    if not traced(case, "FR-7"):
        return []
    reqs = ("FR-7",)
    expected = case["expected"]
    applied = obs.applied or {}
    before = {r["id"] for r in case["input"].get("reminders", [])}
    after = {r["id"] for r in applied.get("reminders", [])}
    target = (action_of(obs) or {}).get("target_reminder_id")
    out = [
        result(
            "property",
            "fr7.operation",
            reqs,
            applied.get("operation") == expected.get("applied_operation"),
            expected.get("applied_operation"),
            applied.get("operation"),
        ),
        result(
            "property",
            "fr7.removed_exactly_target",
            reqs,
            before - after == {target},
            [target],
            sorted(before - after),
        ),
    ]
    out += [
        result(
            "property",
            f"fr7.unchanged.{rid}",
            reqs,
            rid in after,
            "present",
            "present" if rid in after else "missing",
        )
        for rid in expected.get("unchanged_reminder_ids", [])
    ]
    return out


def _is_blank_or_non_text(text: JSON) -> bool:
    return not isinstance(text, str) or not text.strip()


def check_fr8(case: JSON, obs: Observation) -> list[CheckResult]:
    if not traced(case, "FR-8"):
        return []
    reqs = ("FR-8",)
    text = case["input"]["text"]
    action = action_of(obs) or {}
    if _is_blank_or_non_text(text):
        want = case["expected"].get("http_status", 422)
        return [
            result("property", "fr8.status", reqs, obs.status_code == want, want, obs.status_code),
            result("property", "fr8.no_model_call", reqs, obs.model_calls == 0, 0, obs.model_calls),
        ]
    if len(text) > MAX_TEXT:
        too_long = action.get("intent") == "refuse" and action.get("refusal_reason") == "too_long"
        return [
            result(
                "property",
                "fr8.too_long",
                reqs,
                too_long,
                "refuse/too_long",
                action.get("refusal_reason"),
            ),
            result("property", "fr8.no_model_call", reqs, obs.model_calls == 0, 0, obs.model_calls),
        ]
    processed = obs.model_calls >= 1 and action.get("refusal_reason") != "too_long"
    return [
        result(
            "property", "fr8.processed", reqs, processed, "processed by the model", obs.model_calls
        )
    ]


def _signature(obs: Observation) -> tuple[object, object, object]:
    action = action_of(obs) or {}
    when = action.get("datetime_iso")
    instant = parse_instant(when) if isinstance(when, str) else None
    return action.get("intent"), instant, action.get("target_reminder_id")


def check_fr9(case: JSON, runs: list[Observation], k: int) -> list[CheckResult]:
    if not case.get("consistency"):
        return []
    reqs = ("FR-9",)
    signatures = {_signature(r) for r in runs}
    return [
        result("property", "fr9.run_count", reqs, len(runs) == k, k, len(runs)),
        result(
            "property",
            "fr9.identical",
            reqs,
            len(signatures) == 1,
            "identical",
            f"{len(signatures)} distinct",
        ),
    ]
