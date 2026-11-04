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

### Phase 3 US1 sign in (T031-T052)

Red-first failures (the sign-in tests before T040-T051) are not repair events; their summary is in the commit message `test(us1): sign-in tests (red)`. The entries below are unexpected failures seen while making them pass. Fix commit for all of them: `feat(us1): sign in with username and password`.

| # | Failing check and evidence | Expected vs observed | Change made | Re-run (unchanged checks) |
|---|----------------------------|----------------------|-------------|---------------------------|
| 1 | `tests/backend/unit/test_type_hygiene.py::test_every_any_and_type_ignore_in_the_codebase_is_justified` (seen in the red run and again after T044) | Expected pass; observed `tests/backend/unit/test_login_schema.py:52` (and, before the red commit, `test_auth_login.py`) used an unjustified `Any` in a parametrised payload type. | Payload types changed to `dict[str, object]`; no `Any` and no rule change. Files: `tests/backend/unit/test_login_schema.py`, `tests/backend/contract/test_auth_login.py`. | 432 backend tests passed |
| 2 | Lint gate (`.harness/lint.sh`): ruff `S106` (`token_type="bearer"` passed as a keyword literal in `api/v1/auth.py`) and eslint `max-lines-per-function` (`LoginForm`, 72 lines, limit 40) | Expected 0 violations; observed 1 ruff and 1 eslint finding. | The literal moved to a typed constant `BEARER` in `api/schemas/auth.py`; the form split into `components/TextField.tsx`, `hooks/useLoginForm.ts`, and a short `LoginForm`. No configuration changed. | lint exit 0 |

Phase checkpoint T052: integrity, lint, security, test (432 backend, 113 frontend, coverage 98.5% line and 91.4% branch backend, 97.8% frontend), and build pass.

### Phase 4 US2 access protection (T053-T072)

Red-first failures (the access tests before T064-T071) are not repair events; their summary is in the commit message `test(us2): access protection tests (red)`. The entries below are unexpected failures seen while making them pass. Fix commit for all of them: `feat(us2): default-deny gate and session checks`.

| # | Failing check and evidence | Expected vs observed | Change made | Re-run (unchanged checks) |
|---|----------------------------|----------------------|-------------|---------------------------|
| 1 | Full backend run after wiring T064-T069: 26 failures, among them `tests/backend/unit/test_auth_gate.py` (all refusals), `contract/test_auth_bypass.py` (wrong method, malformed JSON) | Expected 401 before any body is read; observed 200 or 422. The installed FastAPI (0.162) keeps routes added with `include_router` as nested `_IncludedRouter` objects, so a gate that walked `app.router.routes` for plain routes saw no match and let every request through. | `api/middleware/auth_gate.py` flattens nested routes (through their `effective_route_contexts()`) before matching; the same flattening builds `public_operations(router)`. File: `src/backend/app/api/middleware/auth_gate.py`. | 13 failures left, all of entries 2 and 3 |
| 2 | `tests/backend/contract/test_route_protection.py::test_the_walk_covers_every_registered_api_route` and the two walk tests | Expected the walk to see every API operation; observed only the operations that are direct `APIRoute` objects (same cause as entry 1). | The walk lists operations from the generated OpenAPI document (public API) instead of `app.routes`; assertions unchanged. File: `tests/backend/contract/test_route_protection.py`. | passed |
| 3 | `tests/backend/contract/test_openapi_contract.py::test_parameters_match_by_name_location_and_required[GET /buses]` (and two more) and `test_status_codes_match[GET /auth/me]` | Expected the app's operations to equal the contract; observed an extra documented `authorization` header parameter and an extra `422` from `require_session` reading the header with `Header()`. | `require_session` reads the credential through `HTTPBearer(auto_error=False)`, which documents a security scheme instead of a parameter and cannot fail validation. File: `src/backend/app/api/deps.py`. | 537 backend tests passed |
| 4 | Lint gate (`.harness/lint.sh`): ruff `E501` (two docstrings in `auth_gate.py`) | Expected 0 violations; observed 2. | Docstrings shortened; no configuration changed. | lint exit 0 |

Phase checkpoint T072: integrity, lint, security, test (537 backend, 134 frontend, coverage 98.6% line and 92.9% branch backend, 99.2% frontend), build, and e2e (18 Playwright tests) pass. The `PENDING` entries for `/auth/me` and the `401` responses are deleted from `tests/backend/contract/test_openapi_contract.py`.

### Phase 5 US3 book as the signed-in user (T073-T085)

No repair needed. Red-first failures (44 backend, 12 frontend) are not repair events; their summary is in the commit message `test(us3): booking as session user (red)`. After T080-T084 no unexpected failure occurred in any task run or gate run.

Phase checkpoint T085: integrity, lint, security, test (538 backend, 128 frontend, coverage 98.4% line and 92.7% branch backend, 99.2% frontend), build, and e2e (19 Playwright tests) pass. The `PENDING` entries for `/users`, `user_id`, and `user_not_found` are deleted from `tests/backend/contract/test_openapi_contract.py`.

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
