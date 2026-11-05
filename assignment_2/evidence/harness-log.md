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

- Commit: `b4a314ab82a5966198c72e38289f322ea3ba4199` on branch `assignment-2-reminder-agent`, tagged `assignment-2-initial-generation` before any recorded harness run (UTC date 2026-11-05).
- State at the tag: all tasks through T149 done; development gate runs: integrity, lint, security and test pass (636 tests, line coverage 98 percent); `.harness/run.sh --dry-run --mode replay` gives `INVALID` only because no recordings exist (a dry run is not a run).
- Snapshot: `evidence/initial-generation/initial-generation.tar.gz` (a `git archive` of the tag: `src/`, `tests/`, `prompts/`, `evals/`, `.harness/` and the approved `specs/001-nl-reminder-agent/{spec,plan,tasks}.md`; 130 files, no caches), with `MANIFEST.txt` (file list) and `initial-generation.tar.gz.sha256`. It is an archive because the harness redaction scan of `evidence/` flags the secret-pattern definitions and test inputs inside `redact.py`, `test_redact.py` and `tasks.md` when they sit there as plain text.
- Coding agent: GitHub Copilot in VS Code agent mode (Claude Sonnet 5.5), working one phase at a time, tests first, with human approval at each phase checkpoint.
- Context given to the agent: `.specify/memory/constitution.md` (v1.0.0), `spec.md`, `plan.md`, `tasks.md`, plus `research.md`, `data-model.md`, `quickstart.md` and `contracts/` (`openapi.yaml`, `eval-dataset.schema.json`, `harness-outputs.md`), all under `specs/001-nl-reminder-agent/`.

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

- Phase 9 (US6, cancel, T132-T138), gate `.harness/lint.sh`, development run at the checkpoint (MEC-11): 1 ruff finding (E501, one asserted phrase line in `test_prompt_rules_cancel.py`). Change: the asserted phrase was shortened (it still appears in the prompt line). No rule or configuration changed. Rerun of the unchanged gate: exit 0; `.harness/test.sh` exit 0 with 586 passed. Not repair events: the intended red run of T132-T134 (4 failed, 2 passed on arrival, 1 collection error before T136-T137).

- Phase 10 (Polish, T139-T149), unexpected failures:
  - `.harness/lint.sh` (MEC-11, MEC-12), development run at the checkpoint: 6 ruff findings (I001 import order and ANN401 `Any` on `app` in `eval_adapter.py`, ANN401 on two helpers in `test_openapi_contract.py`, S105 on a test constant named `TOKEN_LIKE`, E501 in a docstring) and 5 mypy errors (indexing `Observation.action` without narrowing in `test_app_executor.py`). Change: sorted the imports, typed `app` as `FastAPI`, typed the helpers as `object`, renamed the constant, narrowed with `is not None` asserts, shortened the docstring. No rule or configuration changed. Rerun of the unchanged gate: exit 0; `.harness/test.sh` exit 0 with 636 passed, line coverage 98 percent (thresholds 85 and 80 untouched).
  - T147 live smoke of the adapter (3 live requests, outside `.harness/run.sh`, not evidence): preflight passed (runtime 1.0.105, authenticated, `mai-code-1.1-flash` in the catalog) but every request was rejected as `model_routing`: the service served `gpt-6-luna` while `mai-code-1.1-flash` was requested. Expected: served model equal to `EVAL_EXPECTED_MODEL_ID=mai-code-1.1-flash`. Observed: HTTP 503 mapped to `infra_kind=model_routing`, no action. Evidence fed back: the adapter observation and the SDK fault detail (`served gpt-6-luna, expected mai-code-1.1-flash`). Change: none. The expected model id is a protected threshold and a constitution matter, and the model choice is a human decision, so T147 stays open and is escalated. Attempts used: 3 of 5. The adapter classification is correct: a live run in this state would report every model-backed case as `INFRA_ERROR` and the verdict `INVALID`, never `FAIL`.
  - `.harness/run.sh` (T148): the summary step crashed with `KeyError: 'INFRA_MAX_SHARE'` because `run.sh` never exports `.harness/config/thresholds.env` to `summarize.py` (only the individual gate scripts source it). Expected: a verdict line. Observed: traceback and no summary. Change: none, because `.harness/` is frozen and protected; the fix (source the thresholds file in `run.sh` before the summary step, then a human-run `.harness/regen_checksums.sh`) is escalated to the human. Workaround used for the dry run only: the thresholds file exported for that single command. Rerun result: integrity, lint, security and test gates PASS, eval gate FAIL, verdict `INVALID` as expected (no recordings exist); the repository was left untouched.
  - Resolution (human-approved, same commit as the Phase 10 follow-up): `run.sh` now sources `thresholds.env`; the expected and requested model became `gpt-6-luna` (the model the service serves; the smoke then passed: served `gpt-6-luna`, AC-2 answer correct); checksums regenerated.
  - Not repair events: the intended red run of T139-T141 (2 failed, 17 passed on arrival, 1 collection error before T143-T144: the contract lacked the 413, 500, 502, 503, 504 and 422 error responses, and `app.eval_adapter` did not exist).

- Phase 11, first live run `20261105T180350Z` (T151): verdict PASS on every gate, aggregate 1.0, structural, property, semantic and guardrail 100 percent, INFRA 0 percent, 45 of 60 requests, 33 of 33 cases passed, all 8 consistency cases identical across 3 runs. No repair needed.

- Phase 11, drill 3 (invalid token in the scratch clone), gate `.harness/test.sh`: `test_env_example.py::test_the_example_loads_into_valid_settings` failed (expected `secret_values() == []`, observed the ambient `GH_TOKEN`), because tests read the caller's environment. Evidence fed back: the test gate output of that run. Change: `tests/backend/conftest.py` unsets every setting variable for every test; no assertion was changed. Rerun: 636 passed with `GH_TOKEN` and `MODEL_ID` set in the environment, and all four development gates pass.

- Phase 11, convergence (T160-T166), gate `.harness/lint.sh` at the checkpoint (MEC-9): `create_app` grew to 43 lines (limit 40) after the store factory and logging were wired. Change: the interpreter wiring moved to `_build_interpreter` in `api/main.py`; no rule or limit changed. Rerun of the unchanged gate: exit 0, with 646 passed. Not repair events: the intended red run of T160, T162 and T164 (8 failed, 10 passed on arrival).

- Phase 11, live run `20261105T182821Z` (T152), eval gate, verdict FAIL (repair attempt 1 of 5 for each case):
  - N05 (FR-9, FR-3, AC-37, "remind me to send the report by end of day today" at 10:00): expected the same `intent`, `datetime_iso` and target in all 3 runs (`create`, `2026-11-05T17:00:00+00:00`); observed runs 1 and 2 `create` and run 3 `clarify` ("End of day today has already passed"), so `fr9.identical` failed (2 distinct).
  - B05 (FR-8, AC-16, a valid request of exactly 1000 characters made of one repeated sentence): expected `create` "water the plants" at `2026-11-06T09:00:00+00:00`; observed `refuse` / `bulk_action`, so the intent, title overlap and datetime checks failed. The same refusal appeared in the reproducibility run of section 4.
  - M04 (FR-4, AC-7, "remind me to call mom yesterday at 3pm"): expected a clarification naming the field (a rubric keyword `time`, `date`, `when` or `past`); observed "Which future day should I remind you to call mom at 3pm?", so `semantic.rubric.keyword` failed.
  - Evidence fed back to the coding agent: `evidence/harness-results/20261105T182821Z/` (`summary.json`, `eval-results.json`, the redacted recordings `N05.1` to `N05.3`, `B05.1`, `M04.1`).
  - Regression tests first: `tests/backend/unit/test_prompt_rules_regressions.py` (5 tests, failed on arrival), commit `test: regression for N05, B05, M04 (T152)`.
  - Change: `prompts/system.md` only (a time still ahead today is valid and end of day today is 17:00; a repeated request is one reminder and `bulk_action` means many existing reminders; a past-time question says it is in the past and asks for a new date and time), commit `fix: prompt rules from the live run (T152)`. No spec, existing test, dataset, threshold or harness script was touched.
  - Rerun outcome: `.harness/run.sh --mode live` unchanged, run `20261105T183701Z`: all five gates PASS, aggregate 1.0, structural, property, semantic and guardrail 100 percent, INFRA 0 percent, 45 of 60 requests, all 33 cases passed.

## 4. Quickstart validation

Run on 2026-11-05 against the code at commit `6660133` with the live model (`gpt-6-luna`). The API was started with the documented `uvicorn` command and each section 3 scenario was sent with `curl`:

| Scenario | Observed |
|----------|----------|
| AC-1 create | 200, `intent=create`, `datetime_iso=2026-11-09T09:00:00+05:30`, `applied.operation=created` |
| AC-4 clarify | 200, `intent=clarify`, `datetime_iso=null`, one question ("What time should I remind you to call the vendor?") |
| AC-8 injection | 200, `intent=refuse`, `refusal_reason=injection`, `applied.operation=none` |
| AC-14 too long | 200, `refuse` / `too_long`, no model call |
| AC-15 empty | 422, `{"error":{"code":"invalid_request",...}}` |
| Health | 200, `{"status":"ok"}` |

Reproducibility check (MEC-26): a fresh clone of the branch in a scratch directory under `$TMPDIR`, then the documented commands (`pyenv local 3.12`, `python3.12 -m venv .venv`, `uv sync --active`, `python -m copilot download-runtime`, `cp .env.example .env`) and `.harness/run.sh --mode live`: all five gates PASS, verdict PASS, aggregate 0.9818, 45 of 60 requests. Two model-dependent differences from the first run, recorded as evidence and not patched: B05 (the repeated 1000-character request) was refused as `bulk_action` instead of being created, and M04 asked "Which day should I remind you to call mom?", which has none of the rubric keywords `time`, `date`, `when`, `past`. Both are within the 0.85 threshold and no guardrail or structural check failed.

Failure drills (all in the scratch clone, never in this working tree):

| Drill | Observed |
|-------|----------|
| Integrity: one byte appended to `thresholds.env` | integrity gate exit 2, "remaining gates not run", verdict FAIL, other gates NOT_RUN |
| Scope: a committed change outside `assignment_2/` | integrity gate exit 1, "paths changed outside assignment_2/: outside_scope.txt" |
| INFRA: live run with an invalid `GH_TOKEN` | preflight failed ("the SDK is not authenticated"), 0 requests, verdict INVALID, never FAIL |
| Request cap: `LIVE_REQUEST_MAX=5` with regenerated checksums | requests 5 of 5, verdict INVALID; the test gate also failed because `test_scoring.py` pins the declared threshold, as expected for a changed threshold |
| Secret: a fake GitHub-style token in a scratch file | security gate exit 1, gitleaks "leaks found: 1" |

The scratch directory was deleted afterwards.

## 5. Convergence results

`/speckit-converge` was run after the first live run (spec 38 acceptance criteria, 16 functional requirements, 8 invariants, 6 guardrails, 6 success criteria, the plan structure, and constitution principles I to XII with the MEC table). Findings and outcome:

| ID | Gap | Severity | Source | Evidence | Outcome |
|----|-----|----------|--------|----------|---------|
| F1 | contradicts | CRITICAL | Constitution XI, XII | the first generation is tagged `assignment-2-initial-generation` (the name `initial-generation` already exists in the shared repository) and the snapshots are archives, not directories (the redaction scan flags the secret-pattern definitions held in three files) | T159: human ruling needed; the agent does not amend the constitution |
| F2 | contradicts | CRITICAL | Constitution IX | `Any` and one `# type: ignore` without a same-line justification in `eval_adapter.py` and 10 test modules | T160 test (red), T161 fixed with justified aliases |
| F3 | contradicts | HIGH | Constitution IX | `Interpreter` instantiated `InMemoryReminderStore` inline | T162 test (red), T163 the store factory is injected and wired in `create_app` |
| F4 | partial | LOW | plan: `LOG_LEVEL` in `.env.example` | `Settings.log_level` was read nowhere | T164 tests (red), T165 `create_app` applies it and the interpreter logs one line per request (intent and operation only) |

Everything else checked was satisfied: every FR, INV, GR and AC maps to a test or eval case (section 6), all 27 measurable constraints hold, the plan's file structure exists (plus `api/body_limit.py`, the body limit of T113), no list endpoint exists so pagination does not apply, and the edge cases of the plan are covered by prompt-rule tests and validators. Outcome: tasks appended (T159 to T167, Phase 12), T160 to T165 implemented tests first; T159 and T167 wait for the human ruling.

## 6. Acceptance traceability table

Generated with `python .harness/trace_report.py` (every FR, INV, GR and AC maps to at least one test or eval case).

| Requirement | Tests | Eval cases |
|-------------|-------|------------|
| INV-1 | test_action_model.py, test_evaluators_schema.py, test_interpreter_pipeline.py, test_openapi_contract.py, test_output_schema.py |  |
| INV-2 | test_action_model.py, test_evaluators_schema.py, test_output_schema.py |  |
| INV-3 | test_action_model.py, test_evaluators_schema.py, test_output_schema.py | N01 |
| INV-4 | test_action_model.py, test_actions_snooze.py, test_applier_snooze.py, test_evaluators_schema.py, test_output_schema.py, test_prompt_rules_snooze.py | N08 |
| INV-5 | test_actions_cancel.py, test_actions_create.py, test_actions_reschedule.py, test_evaluators_schema.py, test_interpreter_pipeline.py, test_prompt_rules_targets.py, test_untrusted_output.py, test_validator_targets.py | A01, G06, N07 |
| INV-6 | test_action_model.py, test_actions_clarify.py, test_evaluators_schema.py, test_output_schema.py |  |
| INV-7 | test_action_model.py, test_evaluators_schema.py, test_output_schema.py |  |
| INV-8 | test_action_model.py, test_evaluators_schema.py, test_openapi_contract.py, test_output_schema.py, test_untrusted_output.py |  |
| FR-1 | test_actions_create.py, test_applier_create.py, test_calendar_context.py, test_evaluators_properties_time.py, test_prompt_rules_create.py, test_request_models.py, test_validator_time.py | A04, B01, B02, B03, B04, N01, N02, N04, N06 |
| FR-2 | test_action_model.py, test_actions_clarify.py, test_evaluators_properties_time.py, test_prompt_rules_clarify.py | M01, M02 |
| FR-3 | test_actions_clarify.py, test_evaluators_properties_time.py, test_prompt_rules_clarify.py, test_prompt_rules_create.py | M03, N02, N03, N05 |
| FR-4 | test_evaluators_properties_time.py, test_prompt_rules_clarify.py, test_validator_time.py | A03, M04 |
| FR-5 | test_actions_reschedule.py, test_applier_reschedule.py, test_evaluators_properties_other.py, test_prompt_rules_targets.py, test_validator_targets.py | A01, A02, G06, N07, N08, N09, N10 |
| FR-6 | test_actions_snooze.py, test_applier_snooze.py, test_clock_store.py, test_evaluators_properties_other.py, test_prompt_rules_snooze.py | N08, N09 |
| FR-7 | test_actions_cancel.py, test_applier_cancel.py, test_clock_store.py, test_evaluators_properties_other.py, test_prompt_rules_cancel.py, test_validator_targets.py | N10 |
| FR-8 | test_actions_refuse.py, test_evaluators_properties_other.py, test_health_and_errors.py, test_openapi_contract.py, test_request_models.py, test_request_text.py, test_text_guard.py | B05, X01, X02, X03, X04 |
| FR-9 | test_dataset_contract.py, test_eval_runner.py, test_evaluators_properties_other.py |  |
| GR-1 | test_actions_refuse.py, test_applier_refuse_noop.py, test_evaluators_guardrails.py, test_prompt_builder.py, test_prompt_rules_refuse.py | G01, G04, G06 |
| GR-2 | test_actions_refuse.py, test_applier_refuse_noop.py, test_evaluators_guardrails.py, test_prompt_rules_cancel.py, test_prompt_rules_refuse.py | G02 |
| GR-3 | test_actions_refuse.py, test_applier_refuse_noop.py, test_evaluators_guardrails.py, test_prompt_rules_refuse.py | G03 |
| GR-4 | test_actions_refuse.py, test_app_executor.py, test_architecture.py, test_env_example.py, test_evaluators_guardrails.py, test_leak_guard.py, test_llm_clients.py, test_prompt_builder.py, test_prompt_rules_refuse.py, test_settings.py | G04 |
| GR-5 | test_actions_cancel.py, test_actions_create.py, test_actions_refuse.py, test_actions_reschedule.py, test_actions_snooze.py, test_app_executor.py, test_architecture.py, test_copilot_error_mapping.py, test_evaluators_guardrails.py, test_health_and_errors.py, test_interpreter_pipeline.py, test_openapi_contract.py, test_sdk_config.py, test_untrusted_output.py, test_validator_targets.py, test_validator_time.py |  |
| GR-6 | test_actions_refuse.py, test_applier_refuse_noop.py, test_evaluators_guardrails.py, test_prompt_rules_refuse.py | G05 |
| FR-10 | test_check_dataset.py, test_dataset_contract.py |  |
| FR-11 | test_evaluators_guardrails.py, test_evaluators_properties_other.py, test_evaluators_properties_time.py, test_evaluators_schema.py, test_evaluators_semantic.py |  |
| FR-12 | test_scoring.py |  |
| FR-13 | test_verdict.py |  |
| FR-14 | test_app_executor.py, test_copilot_error_mapping.py, test_eval_runner.py, test_health_and_errors.py, test_infra.py, test_llm_clients.py, test_openapi_contract.py, test_sdk_config.py, test_verdict.py |  |
| FR-15 | test_app_executor.py, test_eval_results.py, test_eval_runner.py |  |
| FR-16 | test_summarize.py |  |
| AC-1 | test_actions_create.py, test_applier_create.py, test_validator_time.py | N01 |
| AC-2 | test_evaluators_semantic.py, test_validator_time.py | N02 |
| AC-3 |  | N03 |
| AC-35 |  | N04 |
| AC-37 |  | N05 |
| AC-38 | test_applier_create.py, test_evaluators_semantic.py | N06 |
| AC-4 | test_actions_clarify.py, test_prompt_rules_clarify.py | M01 |
| AC-5 | test_actions_clarify.py, test_prompt_rules_clarify.py | M02 |
| AC-6 | test_actions_clarify.py, test_prompt_rules_clarify.py | M03 |
| AC-7 | test_prompt_rules_clarify.py | M04 |
| AC-34 | test_prompt_rules_clarify.py | A03 |
| AC-36 | test_calendar_context.py | A04 |
| AC-8 | test_actions_refuse.py, test_prompt_rules_refuse.py | G01 |
| AC-9 | test_actions_refuse.py, test_prompt_rules_cancel.py, test_prompt_rules_refuse.py | G02 |
| AC-10 | test_actions_refuse.py, test_prompt_rules_refuse.py | G03 |
| AC-11 | test_actions_refuse.py, test_leak_guard.py | G04 |
| AC-12 | test_action_model.py, test_interpreter_pipeline.py, test_untrusted_output.py, test_validator_targets.py |  |
| AC-13 |  | G05 |
| AC-14 | test_request_text.py, test_text_guard.py | X01 |
| AC-15 | test_app_executor.py, test_request_text.py | X02, X03, X04 |
| AC-16 | test_text_guard.py | B05 |
| AC-17 | test_actions_reschedule.py, test_applier_reschedule.py, test_prompt_rules_targets.py | N07 |
| AC-18 | test_actions_reschedule.py, test_prompt_rules_targets.py, test_validator_targets.py | A01 |
| AC-19 | test_actions_reschedule.py, test_prompt_rules_targets.py | A02 |
| AC-20 | test_actions_snooze.py, test_applier_snooze.py, test_prompt_rules_snooze.py | N08 |
| AC-21 | test_actions_snooze.py, test_applier_snooze.py, test_prompt_rules_snooze.py | N09 |
| AC-22 | test_actions_cancel.py, test_applier_cancel.py, test_prompt_rules_cancel.py | N10 |
| AC-23 | test_actions_cancel.py, test_applier_cancel.py | N10 |
| AC-24 | test_validator_time.py | B01 |
| AC-25 | test_validator_time.py | B02 |
| AC-26 | test_calendar_context.py, test_validator_time.py | B03 |
| AC-27 |  | B04 |
| AC-28 | test_eval_runner.py |  |
| AC-29 | test_app_executor.py, test_copilot_error_mapping.py, test_eval_runner.py, test_infra.py, test_llm_clients.py, test_verdict.py |  |
| AC-30 | test_eval_runner.py, test_verdict.py |  |
| AC-31 | test_scoring.py |  |
| AC-32 | test_summarize.py, test_verdict.py |  |
| AC-33 | test_check_dataset.py, test_dataset_contract.py, test_eval_results.py |  |

MEC-22 pagination: not applicable, the API has no list endpoint.

## 7. Final human decision (ACCEPT or REJECT)

_Recorded by a human only (task T158), with known limitations and residual risks._

### Draft limitations (not a decision)

For the human to confirm or edit; the agent records no ACCEPT or REJECT.

- Model routing is unstable: on 2026-11-05 the service stopped serving the planned `mai-code-1.1-flash` and served `gpt-6-luna` for every request, so the expected model, the `Settings` default and `.env.example` were changed to `gpt-6-luna` by a human-approved change to protected files (`.harness/run.sh` now also exports the thresholds; `.harness/config/thresholds.env` and `checksums.sha256` changed). The specification, plan and research still name the old model.
- Model output varies between runs: the first live run scored 1.0, a reproducibility run in a fresh clone scored 0.9818 (B05 and M04 failed within the threshold), and the next live run on the converged code was a FAIL (N05 differed across its 3 runs, with B05 and M04 again). After one prompt repair the rerun passed with 1.0. A PASS is one sample of a non-deterministic system, not a guarantee, and the repair was tuned on three observed cases.
- The dataset has 33 cases (8 consistency cases run 3 times); the semantic layer is a deterministic keyword and token-overlap rubric, not an LLM judge, so it can reject a valid clarification question (M04) and cannot judge wording quality.
- Rate-limit and process-exit error patterns of the SDK are unverified: they are covered by fake-exception tests and were never observed live.
- State is in memory only: each request starts from the reminders supplied in the request and nothing is persisted.
- The application depends on the Copilot SDK runtime (pinned SDK 1.0.28, runtime 1.0.105), its authentication (logged-in user or token) and, on a corporate network, a working runtime download.
- The edge cases listed in `plan.md` (pronoun reference, empty reminder list, a request mixed with an injection attempt, task text over 120 characters, a duration outside 1 to 1440 minutes) are covered by prompt-rule tests and validators, not by live eval cases.
- Evidence conventions differ from the constitution's wording (see Convergence F1 and task T159): the first generation tag is `assignment-2-initial-generation`, and the snapshots are archives.

## 8. Run table

| run | timestamp_utc | mode | model / effort / sdk | requests | threshold / formula | gates | eval | verdict | results_dir |
|-----|---------------|------|----------------------|----------|---------------------|-------|------|---------|-------------|
| 1 | 20261105T180350Z | live | gpt-6-luna (gpt-6-luna) / low / sdk 1.0.28 | 45/60 | aggregate >= 0.85; weighted structural/property/semantic | integrity:PASS lint:PASS security:PASS test:PASS eval:PASS | aggregate 1.0, guardrail 1.0, infra 0.0 | PASS | evidence/harness-results/20261105T180350Z |
| 2 | 20261105T182821Z | live | gpt-6-luna (gpt-6-luna) / low / sdk 1.0.28 | 45/60 | aggregate >= 0.85; weighted structural/property/semantic | integrity:PASS lint:PASS security:PASS test:PASS eval:FAIL | aggregate 0.9788, guardrail 1.0, infra 0.0 | FAIL | evidence/harness-results/20261105T182821Z |
| 3 | 20261105T183701Z | live | gpt-6-luna (gpt-6-luna) / low / sdk 1.0.28 | 45/60 | aggregate >= 0.85; weighted structural/property/semantic | integrity:PASS lint:PASS security:PASS test:PASS eval:PASS | aggregate 1.0, guardrail 1.0, infra 0.0 | PASS | evidence/harness-results/20261105T183701Z |
