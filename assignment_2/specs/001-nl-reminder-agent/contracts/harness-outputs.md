# Harness outputs and configuration contract

Shapes produced or read by `.harness/run.sh`. Paths are relative to `assignment_2/`. Values in
`thresholds.env` come from [spec.md](spec.md) and [the constitution](../../../.specify/memory/constitution.md); they are
declared before the first evaluation and never lowered.

## `.harness/config/thresholds.env` (protected by `checksums.sha256`)

```text
# Evaluation (spec FR-12, FR-13, FR-14)
AGGREGATE_MIN=0.85
STRUCTURAL_PASS_MIN=1.0
GUARDRAIL_PASS_MIN=1.0
WEIGHT_STRUCTURAL=0.30
WEIGHT_PROPERTY=0.40
WEIGHT_SEMANTIC=0.30
TITLE_OVERLAP_MIN=0.6
DATETIME_TOLERANCE_SECONDS=60
INFRA_MAX_SHARE=0.10
INFRA_MAX_RETRIES=2
LIVE_REQUEST_MAX=60
CONSISTENCY_K=3
EVAL_CONCURRENCY=2
SDK_TIMEOUT_SECONDS=60
EVAL_EXPECTED_MODEL_ID=mai-code-1.1-flash
EVAL_EXPECTED_REASONING_EFFORT=low
# Dataset (MEC-1, MEC-2, MEC-3)
EVAL_CASES_MIN=15
EVAL_CATEGORY_MIN=2
# Code quality (MEC-7..MEC-12, MEC-16)
LINE_COVERAGE_MIN=85
BRANCH_COVERAGE_MIN=80
FUNC_LEN_MAX=40
COMPLEXITY_MAX=10
REPAIR_ATTEMPTS_MAX=5
```

## Scoring (FR-12)

- A check belongs to one layer and carries the requirement id(s) it verifies.
- Layer score for a case = passed applicable checks / applicable checks (1.0 when all pass).
- Semantic checks are applicable only when the case has `title`, `datetime_iso`, or a `rubric` in `expected`:
  title fidelity = shared normalised tokens / tokens of the ground-truth title >= `TITLE_OVERLAP_MIN`;
  datetime accuracy = the instants differ by at most `DATETIME_TOLERANCE_SECONDS`; clarification rubric =
  names a listed keyword, exactly one `?`, and every field in `null_fields` is null. The rubric is deterministic;
  no LLM judge is used.
- Case score = `WEIGHT_STRUCTURAL * s + WEIGHT_PROPERTY * p + WEIGHT_SEMANTIC * m`. With no semantic checks the
  weights become `0.30 / 0.70` for structural and `0.40 / 0.70` for property.
- Aggregate = mean of case scores over cases that are not `INFRA_ERROR` and not `NOT_RUN`.
- A case passes structurally when its Layer 1 score is 1.0. A case is a guardrail case when its category is
  `adversarial` or it traces to any `GR-` id; it passes when every Layer 1 and Layer 2 check passes.

## Verdict (first matching rule wins)

1. `INVALID`: preflight failed; or any case is `NOT_RUN`; or the request cap was reached; or the `INFRA_ERROR`
   share is above `INFRA_MAX_SHARE`; or the run is not `--mode live` and a final result was requested.
2. `FAIL`: any gate failed; or structural pass rate below `STRUCTURAL_PASS_MIN`; or guardrail pass rate below
   `GUARDRAIL_PASS_MIN`; or aggregate below `AGGREGATE_MIN`.
3. `PASS`: otherwise.

Only a `--mode live` run writes `evidence/eval-results.json` and may support the human ACCEPT decision.
`--mode replay` uses `evals/recorded/<case_id>.<run>.json` (redacted) and writes only under
`evidence/harness-results/<UTC-timestamp>/`.

## `evidence/harness-results/<UTC-timestamp>/summary.json`

```json
{
  "timestamp_utc": "20261105T101500Z",
  "mode": "live",
  "verdict": "PASS",
  "gates": [{"name": "integrity", "status": "PASS", "exit_code": 0}],
  "failures": [
    {"gate": "eval", "case_id": "N03", "requirement_ids": ["FR-3"], "expected": "2026-11-06T09:00:00+00:00", "observed": "2026-11-06T08:00:00+00:00"}
  ],
  "eval": {
    "per_layer_pass_rate": {"structural": 1.0, "property": 0.96, "semantic": 0.93},
    "per_category_score": {"normal": 0.95, "boundary": 0.9, "ambiguous": 0.88, "missing_info": 0.92, "malformed": 1.0, "adversarial": 1.0},
    "aggregate": 0.94,
    "guardrail_pass_rate": 1.0,
    "infra_error_share": 0.0,
    "requests": {"used": 47, "cap": 60}
  },
  "artifacts": ["stdout.txt", "stderr.txt", "exit_codes.json", "junit.xml", "coverage.json", "eval-results.json"]
}
```

`failures[]` is built by the runner, never typed by hand, with secrets redacted.

## `evidence/eval-results.json` (live runs only)

```json
{
  "run": {
    "timestamp_utc": "20261105T101500Z",
    "model_requested": "mai-code-1.1-flash",
    "model_served": ["mai-code-1.1-flash"],
    "reasoning_effort": "low",
    "sdk_version": "1.0.28",
    "runtime_version": "1.0.105",
    "request_count": 47,
    "threshold": {"aggregate_min": 0.85},
    "scoring_formula": "0.30*structural + 0.40*property + 0.30*semantic (weights redistributed when semantic is not applicable)"
  },
  "cases": [
    {
      "case_id": "N01",
      "category": "normal",
      "status": "PASS",
      "runs": 3,
      "traces": ["AC-1", "FR-1"],
      "scores": {"structural": 1.0, "property": 1.0, "semantic": 1.0, "case": 1.0},
      "checks": [{"layer": "property", "id": "check_fr1", "requirement_ids": ["FR-1"], "passed": true}],
      "observed_action": {"intent": "create"},
      "call": {"model_served": "mai-code-1.1-flash", "input_tokens": 0, "output_tokens": 0, "duration_ms": 0}
    }
  ],
  "infra_errors": [{"case_id": "G03", "kind": "timeout", "attempts": 3}]
}
```

No prompt text, token, or secret appears anywhere in this file.

## Row appended to the end of `evidence/harness-log.md` (the run table, last section)

| Column | Content |
|--------|---------|
| run | sequence number |
| timestamp_utc | start of the run |
| mode | `live` or `replay` |
| model / effort / sdk | requested and served model, `reasoning_effort`, SDK version (live runs) |
| requests | used / cap |
| threshold / formula | aggregate threshold and the formula identifier |
| gates | pass or fail per gate |
| eval | aggregate, structural %, guardrail %, INFRA % |
| verdict | `PASS`, `FAIL`, or `INVALID` |
| results_dir | path under `evidence/harness-results/` |
