# Harness Log: Natural-Language Reminder Agent

Feature: `specs/001-nl-reminder-agent/` on branch `assignment-2-reminder-agent`. Sections follow the order required by the constitution. The run table is last and is appended to only by `.harness/run.sh`.

## 1. Human Approval

Implementation (task T002 onward) MUST NOT start until a human fills in every line below. The agent does not write this section's decisions.

| Artifact | Last modified | Decision | Name | Date |
|----------|---------------|----------|------|------|
| `specs/001-nl-reminder-agent/spec.md` | 2026-11-05 | APPROVED | Siddharth | 2026-11-05 |
| `specs/001-nl-reminder-agent/plan.md` | 2026-11-05 | APPROVED | Siddharth | 2026-11-05 |
| `specs/001-nl-reminder-agent/tasks.md` | 2026-11-05 | APPROVED | Siddharth | 2026-11-05 |
| `.specify/memory/constitution.md` (v1.0.0) | 2026-11-05 | APPROVED | Siddharth | 2026-11-05 |

Write `APPROVED` (or `REJECTED` with the reason) in the Decision column, then your name and the date.

Foundational checkpoint (task T057, before any application code):

| Checkpoint | Decision | Name | Date |
|------------|----------|------|------|
| Foundational A (harness) | APPROVED | Siddharth | 2026-11-05 |

Other human-recorded approvals (for example a regenerated `.harness/config/checksums.sha256`) are added below as one line each.

## 2. Initial generation and context

_To be completed in task T150._

## 3. Failure-and-repair log

_Entries are added when a genuine, unexpected failure occurs. A phase with no failure is logged as "no repair needed"._

- Phase 1 (Setup, T003-T011): no repair needed.

- Phase 2 (Foundational A, harness), gate `.harness/lint.sh`, development run before the checksums were generated (T055):
  - Failed rules: MEC-9 (function length at most 40 lines), MEC-11 (ruff findings 0), MEC-12 (mypy --strict errors 0).
  - Expected versus observed: expected 0 ruff findings, 0 mypy errors, no function above 40 lines. Observed 37 ruff findings (E501 line length, ANN missing annotations on test doubles), 74 mypy errors in 9 test files (a list-invariant parameter type in the shared `passed_map` helper, untyped helpers, unused `type: ignore` comments), 1 mypy error in `.harness/eval_runner.py` (untyped lambda), and `evaluators/semantic.py:_rubric` at 46 lines.
  - Evidence fed back to the coding agent: the full stdout of `.harness/lint.sh` (ruff, mypy, function-length output).
  - Change made (Phase 2 milestone commit `chore: deterministic harness, dataset, thresholds, integrity checksums`): typed `passed_map` over `Sequence[CheckResult]` in `tests/backend/unit/harness_helpers.py`; annotated or aliased the test doubles and removed unneeded `type: ignore` comments in `tests/backend/unit/test_*.py`; replaced the lambda with `functools.partial` in `.harness/eval_runner.py`; split `_rubric` through a `_semantic` helper in `.harness/evaluators/semantic.py`; shortened long lines in `.harness/summarize.py` and `.harness/trace_report.py`; ruff applied formatting and import order. No rule, threshold, or tool configuration was changed.
  - Re-run outcome of the same gate unchanged: `.harness/lint.sh` exit 0 (ruff, format check, mypy --strict, function length). `pytest` 165 passed, `.harness/security.sh` exit 0.
  - Not repair events: the intended red run of the new tests (T031, 18 modules failed to import) and the expected skeleton failures of `.harness/run.sh --dry-run` (zero coverage statements, no contract tests, AC-12 uncovered, no `app.eval_adapter`), all of which belong to Phase 3 onward.

## 4. Quickstart validation

_To be completed in task T154._

## 5. Convergence results

_To be completed in task T155._

## 6. Acceptance traceability table

_To be generated in task T153 with `python .harness/trace_report.py`._

## 7. Final human decision (ACCEPT or REJECT)

_Recorded by a human only (task T158), with known limitations and residual risks._

## 8. Run table

| run | timestamp_utc | mode | model / effort / sdk | requests | threshold / formula | gates | eval | verdict | results_dir |
|-----|---------------|------|----------------------|----------|---------------------|-------|------|---------|-------------|
