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

- Phase 3 (Foundational B, application core), unexpected failures in task test runs and the lint gate, all repaired in the Phase 3 milestone commit `feat: application core (T058-T087)`:
  - Test helpers: `tests/backend/unit/app_helpers.py::create_dict` and `test_action_model.py::_snooze` passed an overridable field as an explicit keyword, so `create_dict(title=None)` raised `TypeError: got multiple values for keyword argument` at collection (expected: helper accepts overrides; observed: collection error in `test_action_model.py`). Fix: merge the base dict with the overrides. Rerun of the same tests: collected and passed.
  - `test_prompt_builder.py::test_the_real_template_declares_data_not_instructions_and_holds_the_canary` (GR-1): expected the phrase "data, never instructions" in `prompts/system.md`; observed the phrase split across two lines by my hard wrap. Evidence fed back: the assertion diff. Fix: the sentence is on one line in `prompts/system.md`. Rerun: 327 passed.
  - `.harness/lint.sh` (MEC-11, MEC-12): 3 findings after formatting (E501 in one test docstring, RUF012 mutable class attribute in `test_sdk_config.py`, one mypy error on an untyped `*responses` parameter in `test_health_and_errors.py`). Fix: shortened the docstring, `ClassVar`, typed the helper with `Scripted`. Rerun of the unchanged gate: exit 0.
  - Not repair events: the intended red run of T058-T070 (12 test modules failed at collection because `app` modules did not exist).
  - Upstream artifact change found while implementing (recorded here per Principle I): the uniform error body also covers framework HTTP errors, so `contracts/openapi.yaml` (`ErrorBody.code` enum) and `data-model.md` (Errors table) gained `not_found` (404) and `method_not_allowed` (405). No requirement, acceptance criterion, or threshold changed.

- Phase 4 (US1, create), gate `.harness/test.sh`, development run at the checkpoint (T096), repaired in the Phase 4 milestone commit `feat(us1): create reminder (T088-T095)`:
  - Failing test: `tests/backend/unit/test_interpreter_pipeline.py::test_an_intent_without_a_registered_handler_is_a_programming_error` (GR-5, programming-error path for an unregistered intent).
  - Expected versus observed: expected `UnregisteredIntentError` for a valid `create` action; observed `DID NOT RAISE` (1 failed, 391 passed) because the test relied on `create` having no handler, which was only true before `CreateHandler` was registered in T094.
  - Evidence fed back: the pytest failure output for that test.
  - Change made: the test builds its `Applier` with an empty handler registry (`Applier({})`) so the precondition no longer depends on which intents have handlers; the assertion is unchanged. No rule, threshold, or other test was changed.
  - Rerun result: `.harness/test.sh` exit 0, 392 passed; `.harness/lint.sh` and `.harness/security.sh` exit 0.
  - Not repair events: the intended red run of T088-T091 (38 failed, 18 passed, 1 collection error before T093-T095).

- Phase 5 (US2, clarify, T097-T101): no repair needed. Not repair events: the intended red run of T097 (12 prompt-rule tests failed before T100; the 6 contract tests in `test_actions_clarify.py` and the "one question" phrase passed on arrival because Phase 3 already enforces INV-6 and the output contract section already states the 200-character limit).

- Phase 6 (US3, refuse and untrusted output, T102-T115), unexpected failures repaired in the Phase 6 milestone commit `feat(us3): refusal, guardrails and untrusted-output handling (T102-T114)`:
  - `tests/backend/unit/test_untrusted_output.py` (GR-5, AC-12), cases `extra-field`, `intent-not-allowed`, `missing-required-field`, and the contract test `test_a_schema_invalid_output_is_502_and_never_a_partial_action`: expected `LLMOutputError` (502 `model_output_invalid`); observed the raw pydantic `ValidationError` (a 500 `internal_error` through the API), because `StubLLMClient` validated the scripted dict itself without mapping the error, unlike `CopilotLLMClient` and `ReplayLLMClient`. Evidence fed back: the pytest failure output. Change: the stub maps `ValidationError` to `LLMOutputError("schema")`, so every client reports a bad wire shape the same way. No assertion was changed. Rerun: the cases pass.
  - `.harness/lint.sh` (MEC-11, MEC-12), development run at the checkpoint: 7 ruff findings (E501 in three test docstrings, S105 on a test constant named `SECRET`, ANN401 on two `Any` parameters or returns in `test_actions_refuse.py`) and 1 mypy error (`no-any-return` in the same file). Change: shortened the docstrings, renamed the constant, typed the helper with named parameters and `httpx.Response`. No rule or configuration changed. Rerun of the unchanged gate: exit 0.
  - Rerun result: `.harness/test.sh` exit 0 with 500 passed; integrity, lint and security exit 0.
  - Not repair events: the intended red run of T102-T108 (31 failed, 35 passed on arrival, 2 modules failed at collection before T110-T114).

- Phase 7 (US4, reschedule, T116-T124), gate `.harness/lint.sh`, development run at the checkpoint (MEC-11, MEC-12): 3 ruff findings (E501 in `applier.py` and two phrase lines in `test_prompt_rules_targets.py`) and 1 mypy error (`**` of an untyped dict in `test_validator_targets.py`). Change: shortened the lines (the asserted phrases still appear in the prompt) and typed the `TARGETED` table. No rule or configuration changed. Rerun of the unchanged gate: exit 0; `.harness/test.sh` exit 0 with 551 passed. Not repair events: the intended red run of T116-T119 (10 failed, 38 passed on arrival, 1 collection error before T121-T123).

- Phase 8 (US5, snooze, T125-T131), gate `.harness/lint.sh`, development run at the checkpoint (MEC-12): 1 mypy error in `test_applier_snooze.py` (`**dict[str, object]` passed to the typed `request` helper). Change: the helper call uses explicit keyword arguments. No rule or configuration changed. Rerun of the unchanged gate: exit 0; `.harness/test.sh` exit 0 with 574 passed. Not repair events: the intended red run of T125-T127 (6 failed, 4 passed on arrival, 1 collection error before T129-T130).

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
