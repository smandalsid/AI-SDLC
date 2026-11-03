# Harness Log: 002-user-authentication (User Authentication for Bus Booking)

Chronological record required by constitution v1.4.1 (Principles XII and XIII). Feature 001's record is archived,
unedited, in `evidence/001-seat-booking/`.

## Approval

Implementation MUST NOT start until a human replaces `PENDING` below with `APPROVED`, their name, and the
date. The coding agent MUST NOT write this decision.

| Artifact | Last modified | Decision | Approved by | Date |
|----------|---------------|----------|-------------|------|
| `specs/002-user-authentication/spec.md` | 2026-11-03 | APPROVED | Siddharth | 2026-11-03 |
| `specs/002-user-authentication/plan.md` | 2026-11-03 | APPROVED | Siddharth | 2026-11-03 |
| `specs/002-user-authentication/tasks.md` | 2026-11-03 | APPROVED | Siddharth | 2026-11-03 |
| `.specify/memory/constitution.md` (v1.4.1) | 2026-11-03 | APPROVED | Siddharth | 2026-11-03 |

Decisions confirmed by the human at T001 (2026-11-03): the evidence layout (branch `002-user-authentication`,
feature 001 evidence archived with `git mv` into `evidence/001-seat-booking/`, first generation tagged
`002-initial-generation`) and the planned extension of `.harness/redact.sh` (tasks T006-T007; the diff is shown and
approved again at T007, and the human regenerates the checksums).

## Initial generation and context

Filled by T128.

## Failure and repair log

Filled when failures happen (constitution XII, v1.4.1). Each phase ends with its entries or "no repair needed".

### Phase 2 Foundational (T008-T030)

Red-first failures (the foundation tests before T018-T029) are not repair events; their summary is in the commit message `test(auth): foundation tests (red)`. The entries below are unexpected failures seen while making them pass. Fix commit for all of them: `feat(auth): foundation (settings, hashing, tokens, schema, seed)`.

| # | Failing check and evidence | Expected vs observed | Change made | Re-run (unchanged checks) |
|---|----------------------------|----------------------|-------------|---------------------------|
| 1 | Full backend run after T018-T028: `tests/backend/contract/test_openapi_contract.py::test_the_contract_lists_exactly_the_error_codes_the_app_defines` | Expected pass; observed the compared contract lacked the error codes the app now defines (`unauthenticated`, `invalid_credentials`, `too_many_attempts`). Loading the 002 contract then exposed a YAML syntax error (unquoted `: ` in the `access_token` description). | Test repointed to `specs/002-user-authentication/contracts/openapi.yaml` with an explicit `PENDING` list that each story checkpoint empties (the staged comparison of T035, pulled forward because the new codes made the 001 contract unusable); contract YAML fixed by quoting the description (documentation fix, no spec change). Files: `tests/backend/contract/test_openapi_contract.py`, `specs/002-user-authentication/contracts/openapi.yaml`. | 23 passed |
| 2 | Same run: `tests/backend/unit/test_seed_credentials.py::test_seed_cli_exits_non_zero_and_prints_no_password_when_an_entry_is_missing` | Expected exit code 2 before any database access; observed a database login attempt. Dict-typed settings are merged across sources, so the real `.env` `MOCK_USER_PASSWORDS` filled the missing entries. | Test now builds `Settings(_env_file=None)` through a monkeypatch, so a unit test never reads the real `.env`. File: `tests/backend/unit/test_seed_credentials.py`. | passed |
| 3 | Checkpoint run: `tests/backend/unit/test_architecture.py::test_gate_middleware_module_exists_without_data_layer_imports` and `src/frontend/tests/architecture.test.ts` "has the session store module" | Expected pass at the foundation checkpoint; observed failure: both assert the existence of modules delivered by later stories (`api/middleware/auth_gate.py` in US2, `api/session.ts` in US1). Test-design error: the checks belong to those stories. | Existence checks removed from the foundation tests and re-homed: the gate-module check to T053, the session-module check is implied by `session.test.ts` (T036). The layering and storage rules themselves stay in force. Files: `tests/backend/unit/test_architecture.py`, `src/frontend/tests/architecture.test.ts`. | 376 backend and 76 frontend tests passed |
| 4 | Lint gate (`.harness/lint.sh`): ruff `S105` (`_DUMMY_SECRET` literal in `core/passwords.py`), `E501` (`db/seed.py`), mypy `arg-type` (`**dict` into the argon2 constructor in `core/passwords.py`) and mypy `misc` (`column_info` return type in `tests/backend/integration/test_auth_schema_and_seed.py`) | Expected 0 violations; observed 2 ruff and 3 mypy findings. | Dummy input generated at runtime with `secrets.token_urlsafe`; explicit argon2 default constants instead of `**dict`; message wrapped; helper typed with `ReflectedColumn`. No configuration changed. | lint exit 0 (ruff, format, mypy, function length, eslint, tsc) |

Phase checkpoint T030: integrity, lint, security, test (376 backend, 76 frontend, coverage 98.3% line and 90.4% branch backend, 99.3% frontend), and build pass.

## Quickstart validation

Filled by T131.

## Convergence results

Filled by T132.

## Acceptance traceability

Filled by T125.

### Functional requirements

| Requirement | Test(s) | Result |
|-------------|---------|--------|

### Non-functional requirements

| Requirement | Test(s) | Result |
|-------------|---------|--------|

### Success criteria

| Criterion | Test(s) | Result |
|-----------|---------|--------|

### Acceptance scenarios

| Scenario | Test(s) | Result |
|----------|---------|--------|

### Edge cases

| Edge case | Test(s) | Result |
|-----------|---------|--------|

## Final decision

Recorded by the human at T134. The agent MUST NOT write the decision.

## Harness run table

| Timestamp | Integrity | Lint | Security | Tests | Build | E2E | Result | Evidence |
|-----------|-----------|------|----------|-------|-------|-----|--------|----------|
