"""Scoring formula and the threshold loader (spec FR-12)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from evaluators.common import CheckResult


@dataclass(frozen=True)
class Weights:
    structural: float
    property: float
    semantic: float

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Weights:
        return cls(
            float(env["WEIGHT_STRUCTURAL"]),
            float(env["WEIGHT_PROPERTY"]),
            float(env["WEIGHT_SEMANTIC"]),
        )


@dataclass(frozen=True)
class Thresholds:
    aggregate_min: float
    structural_pass_min: float
    guardrail_pass_min: float
    weights: Weights
    title_overlap_min: float
    datetime_tolerance_seconds: float
    infra_max_share: float
    infra_max_retries: int
    live_request_max: int
    consistency_k: int
    eval_concurrency: int
    expected_model_id: str
    expected_reasoning_effort: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Thresholds:
        return cls(
            aggregate_min=float(env["AGGREGATE_MIN"]),
            structural_pass_min=float(env["STRUCTURAL_PASS_MIN"]),
            guardrail_pass_min=float(env["GUARDRAIL_PASS_MIN"]),
            weights=Weights.from_env(env),
            title_overlap_min=float(env["TITLE_OVERLAP_MIN"]),
            datetime_tolerance_seconds=float(env["DATETIME_TOLERANCE_SECONDS"]),
            infra_max_share=float(env["INFRA_MAX_SHARE"]),
            infra_max_retries=int(env["INFRA_MAX_RETRIES"]),
            live_request_max=int(env["LIVE_REQUEST_MAX"]),
            consistency_k=int(env["CONSISTENCY_K"]),
            eval_concurrency=int(env["EVAL_CONCURRENCY"]),
            expected_model_id=env["EVAL_EXPECTED_MODEL_ID"],
            expected_reasoning_effort=env["EVAL_EXPECTED_REASONING_EFFORT"],
        )


def layer_score(checks: Sequence[CheckResult]) -> float | None:
    """Fraction of applicable checks that passed; None when the layer has none."""
    if not checks:
        return None
    return sum(1 for c in checks if c.passed) / len(checks)


def case_score(
    structural: float | None, prop: float | None, semantic: float | None, weights: Weights
) -> float:
    """Weighted score over the layers that have applicable checks, weights renormalised."""
    parts = [
        (weights.structural, structural),
        (weights.property, prop),
        (weights.semantic, semantic),
    ]
    present = [(w, s) for w, s in parts if s is not None]
    total = sum(w for w, _ in present)
    if not present or total == 0:
        return 0.0
    return round(sum(w * s for w, s in present) / total, 4)


def aggregate(scores: Sequence[float]) -> float:
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)
