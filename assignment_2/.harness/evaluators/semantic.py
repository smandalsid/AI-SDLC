"""Layer 3: deterministic semantic and quality checks (no LLM judge)."""

from __future__ import annotations

import re

from evaluators.common import JSON, CheckResult, Observation, action_of, parse_instant, result

_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def title_overlap(observed: str, truth: str) -> float:
    wanted = tokens(truth)
    return len(tokens(observed) & wanted) / len(wanted) if wanted else 0.0


def _title(case: JSON, action: JSON, minimum: float) -> list[CheckResult]:
    truth = case["expected"].get("title")
    if truth is None:
        return []
    title = action.get("title")
    overlap = title_overlap(title, truth) if isinstance(title, str) else 0.0
    return [
        result(
            "semantic",
            "semantic.title",
            ("FR-11",),
            overlap >= minimum,
            f"overlap >= {minimum} with {truth!r}",
            title,
        )
    ]


def _datetime(case: JSON, action: JSON, tolerance: float) -> list[CheckResult]:
    truth = case["expected"].get("datetime_iso")
    if truth is None:
        return []
    given = action.get("datetime_iso")
    ok = False
    if isinstance(given, str):
        ok = abs((parse_instant(given) - parse_instant(truth)).total_seconds()) <= tolerance
    return [result("semantic", "semantic.datetime", ("FR-11",), ok, truth, given)]


def _semantic(name: str, passed: bool, expected: object, observed: object) -> CheckResult:
    return result("semantic", f"semantic.{name}", ("FR-11",), passed, expected, observed)


def _rubric(case: JSON, action: JSON) -> list[CheckResult]:
    expected = case["expected"]
    rubric = expected.get("rubric")
    if rubric is None:
        return []
    question = action.get("clarification_question")
    text = question.lower() if isinstance(question, str) else ""
    keywords = rubric.get("names_field", [])
    out: list[CheckResult] = []
    if keywords:
        hit = any(k.lower() in text for k in keywords)
        out.append(_semantic("rubric.keyword", hit, f"one of {keywords}", question))
    if rubric.get("single_question", True):
        asked = text.count("?")
        out.append(_semantic("rubric.single_question", asked == 1, "exactly one question", asked))
    null_fields = expected.get("null_fields", [])
    if rubric.get("invents_nothing", True) and null_fields:
        invented = [f for f in null_fields if action.get(f) is not None]
        out.append(_semantic("rubric.invents_nothing", not invented, "nothing invented", invented))
    return out


def run_semantic(
    case: JSON, obs: Observation, title_min: float, tolerance_seconds: float
) -> list[CheckResult]:
    action = action_of(obs)
    expected = case["expected"]
    if not any(k in expected for k in ("title", "datetime_iso", "rubric")):
        return []
    action = action or {}
    return (
        _title(case, action, title_min)
        + _datetime(case, action, tolerance_seconds)
        + _rubric(case, action)
    )
