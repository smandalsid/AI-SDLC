---

description: "Task list for feature 001-seat-booking (Bus Seat Booking), harness-first"
---

# Tasks: Bus Seat Booking

**Input**: Design documents from `/specs/001-seat-booking/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md; constitution v1.3.1

**Tests**: REQUIRED and written first (constitution V, XIII). Every test task precedes the implementation tasks it covers, and a "confirm failing" task proves the tests fail before any implementation starts.

**Organization**: Tasks are grouped by user story. US1, US2, US3 are P1; US4 is P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 = view bus and seats, US2 = book seats, US3 = protection and visibility, US4 = choose user
- Paths follow plan.md: backend `src/backend/`, backend tests `tests/backend/`, frontend `src/frontend/`, frontend tests `src/frontend/tests/`, harness `.harness/`, evidence `evidence/`

## Guardrails for every task (constitution XII and XIII)

- **Approval gate**: T001 is a human gate. No task after T001 may start until a human has recorded `APPROVED`, their name, and the date in `evidence/harness-log.md`.
- **No running ahead**: implement one phase at a time. At every `Checkpoint` task, stop, report the completed tasks and the gate results, and halt on the first failing non-parallel task. Mark a task `[X]` only after its tests pass.
- Never put secret values in any file, log, or evidence artifact; read them only through `app/core/config.py`.
- Never weaken, skip, or delete a test or assertion, relax a lint/type/security/coverage setting, edit `.harness/config/`, the lint/type configuration (`src/backend/ruff.toml`, `src/backend/mypy.ini`, `src/frontend/eslint.config.js`, `src/frontend/tsconfig.json`), or edit recorded harness results to get a PASS. Spec changes go through spec.md, plan.md, tasks.md and git history.
- Development runs of the individual gate scripts (`.harness/lint.sh`, `test.sh`, ...) are allowed at checkpoints but are not evidence. Only `.harness/run.sh` (T129 onward) creates evidence, and only after the `initial-generation` snapshot (T128).
- Every phase checkpoint runs `integrity.sh`, `lint.sh`, `security.sh`, and `test.sh`, plus `build.sh` once the frontend can build (T080 onward) and `e2e.sh` once an e2e spec exists (T116 onward) (constitution XII). A gate that cannot run yet is named in the checkpoint report, never skipped silently.
- Do not touch `.env`; do not stop or remove the running `azure-sql-edge` container; do not touch other databases on it (for example `mid_dev`); both without explicit user confirmation.

---

## Phase 1: Setup (Approval, Environment, Skeleton)

**Purpose**: Human approval, environment, project skeleton, and tool configuration

- [X] T001 Create `evidence/harness-log.md` with a header, an "Approval" section listing `specs/001-seat-booking/spec.md`, `plan.md`, `tasks.md`, and `.specify/memory/constitution.md` (with last-modified dates), and empty placeholder sections in the order the constitution requires: Initial generation and context, Failure and repair log, Quickstart validation, Convergence results, Acceptance traceability, Final decision; STOP and wait for a human to record `APPROVED`, their name, and the date in the Approval section. The agent MUST NOT write the decision itself
- [X] T002 Commit the approved artifacts as `docs: approved constitution v1.3.1, spec, plan, tasks` (stage `specs/`, `.specify/`, `.github/`, and `evidence/harness-log.md`; never `.env`)
- [X] T003 [P] Extend `.gitignore` (keep existing `.env`, `.venv`, `.DS_Store`) with `node_modules`, `dist`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `coverage`, `htmlcov`, `playwright-report`, `test-results`
- [X] T004 [P] Create `.env.example` with variable names and placeholder values only: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=localhost`, `DB_PORT=1433`, `CORS_ORIGINS=http://localhost:5173`
- [X] T005 Run `pyenv local 3.12` (writes `.python-version`), then `python3.12 -m venv .venv` at the repository root and activate it; confirm `python --version` prints 3.12.x
- [X] T006 Create `src/backend/pyproject.toml`: project `bus-booking-api`, `requires-python = ">=3.12,<3.13"`; runtime deps `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `sqlalchemy` (2.0.x), `pymssql`, `alembic`; dev group `pytest`, `pytest-cov`, `httpx2`, `ruff`, `mypy`, `bandit`, `pip-audit`, `pyyaml`, `types-PyYAML`; pytest (`testpaths = ["../../tests/backend"]`, `pythonpath = ["."]`, marker `perf`), coverage (`branch = true`, `source = ["app"]`); coverage and other numeric thresholds are NOT set here, they live only in `.harness/config/thresholds.env`; also create `src/backend/ruff.toml` (`line-length = 100`, rules `E,F,I,B,C90,S,UP`, `S101` ignored only under tests; no complexity number, `lint.sh` injects `COMPLEXITY_MAX`) and `src/backend/mypy.ini` (`strict = True`, pydantic plugin); both are checksummed by T028
- [X] T007 Install with `source .venv/bin/activate && cd src/backend && uv sync --active`; verify the packages are under the root `.venv` (`python -c "import fastapi; print(fastapi.__file__)"`) and keep the generated `src/backend/uv.lock` for commit
- [X] T008 [P] Create the directory skeleton from plan.md: `src/backend/app/{core,models,repositories,services,db}`, `src/backend/app/api/{schemas,v1}`, `src/backend/migrations/versions`, `tests/backend/{unit,contract,integration}`, `src/frontend/{src,tests,e2e}`, `scripts`, `.harness/config`; add `__init__.py` to every Python package directory (not `migrations/`)
- [X] T009 [P] Create `src/frontend/package.json` (scripts `dev`, `build`, `test`, `coverage`, `lint`, `typecheck`, `e2e`), `tsconfig.json` (`"strict": true`), and `index.html`; `npm install` `react`, `react-dom`, `react-router-dom` and dev deps `vite`, `@vitejs/plugin-react`, `typescript`, `vitest`, `jsdom`, `@vitest/coverage-v8`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `@testing-library/dom`, `eslint`, `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `@playwright/test`, `@types/react`, `@types/react-dom`; keep `package-lock.json`
- [X] T010 [P] Create `src/frontend/eslint.config.js`: `typescript-eslint` strict, `no-explicit-any` as error, `react-hooks`, `max-lines-per-function` for `src/**` with the limit read from `process.env.FUNCTION_MAX_LINES` (exported by `lint.sh`; no literal number, and the config throws if it is unset), and `no-restricted-globals` for `fetch` inside `src/components` and `src/pages`
- [X] T011 [P] Create `src/frontend/vite.config.ts` (React plugin, dev proxy `/api` to `http://127.0.0.1:8000`, Vitest `environment: "jsdom"`, `setupFiles: ["tests/setup.ts"]`, coverage provider v8; the coverage threshold is enforced by `.harness/test.sh`, not here) and `src/frontend/tests/setup.ts` (jest-dom matchers, cleanup)
- [X] T012 [P] Create `docker-compose.yml` with service `azure-sql-edge` (`mcr.microsoft.com/azure-sql-edge`, port 1433, `ACCEPT_EULA=1`, `MSSQL_SA_PASSWORD` from `${DB_PASSWORD}` via `.env`, TCP healthcheck `bash -c 'echo > /dev/tcp/127.0.0.1/1433'`, named volume); validate the YAML only (the `docker compose` plugin is not installed) and do not start it here; `scripts/dev.sh` (T122) is the only script that starts the container
- [X] T013 [P] Verify gate tooling is installed: `gitleaks version` (install with Homebrew if missing; if the corporate proxy blocks it, download via a browser) and the Playwright browser: Chromium download is blocked by the proxy and Edge forbids remote debugging by policy, so confirm `/Applications/Google Chrome Canary.app` exists and use `channel: "chrome-canary"` in `playwright.config.ts`; report any blocker to the user instead of skipping a gate
- [X] T014 [P] Create `evidence/initial-generation/.gitkeep`, `evidence/final-generation/.gitkeep`, `evidence/harness-results/.gitkeep`, and append the empty run table to the END of `evidence/harness-log.md` (header `| Timestamp | Integrity | Lint | Security | Tests | Build | E2E | Result | Evidence |`); sections are already in the constitution's order (T001), so no section is ever inserted; the run table stays last

---

## Phase 2: Foundational (Harness First, then Core Infrastructure)

**Purpose**: The deterministic harness MUST exist before any application code (constitution XII); then configuration, errors, models, migration, database tooling, app factory, test fixtures, and the frontend API foundation. Every implementation task is preceded by its failing test task.

**CRITICAL**: No user story work begins until this phase is complete

### Harness (Principle XII)

- [X] T015 [P] Create `.harness/config/thresholds.env`: `BACKEND_COVERAGE_LINE_MIN=85`, `BACKEND_COVERAGE_BRANCH_MIN=80`, `FRONTEND_COVERAGE_LINE_MIN=80`, `SAST_FAIL_LEVEL=medium`, `AUDIT_FAIL_LEVEL=high`, `BUNDLE_MAX_KB_GZIP=200`, `FUNCTION_MAX_LINES=40`, `COMPLEXITY_MAX=10`, `READ_P95_MS=300`, `WRITE_P95_MS=500`; changes require a constitution amendment; also create `.harness/config/gitleaks.toml`: `[extend] useDefault = true` and an `[allowlist]` for the paths `(^|/)\.env$`, `(^|/)\.venv/`, and `(^|/)node_modules/` only (the git-ignored `.env` legitimately holds the real DB password)
- [X] T016 [P] Create `.harness/lint.sh` (gate 1): `set -a; source .harness/config/thresholds.env; set +a` so the thresholds are exported, then from the root `.venv` run `ruff check --config "lint.mccabe.max-complexity=$COMPLEXITY_MAX"`, `ruff format --check`, `mypy` on `src/backend` and `tests/backend`, `python .harness/check_function_length.py`, then `eslint . --max-warnings 0` (reads `FUNCTION_MAX_LINES` from the environment) and `tsc --noEmit` in `src/frontend`; run every check, exit non-zero if any failed
- [X] T017 [P] Create `.harness/security.sh` (gate 2): `bandit -r src/backend/app` at the level mapped from `SAST_FAIL_LEVEL`, `pip-audit` (project path excluded if not on PyPI), `npm audit --audit-level=$AUDIT_FAIL_LEVEL` in `src/frontend`, `gitleaks dir . --config .harness/config/gitleaks.toml --no-banner` on the working tree (this includes `evidence/`) and `gitleaks git . --config .harness/config/gitleaks.toml --no-banner` on committed history (`gitleaks detect` is deprecated in 8.30); run every check, exit non-zero if any failed
- [X] T018 [P] Create `.harness/test.sh` (gate 3): `pytest --cov --cov-branch` with `--cov-report=json` and `--junitxml` into `$HARNESS_OUT`, then `vitest run --coverage --reporter=junit` for the frontend; a Python check computes backend line % (`covered_lines / num_statements`) and branch % (`covered_branches / num_branches`) from `coverage.json`, reads the frontend line % from its coverage summary, compares all three with `thresholds.env`, and fails on any skipped or xfail test in either junit file
- [X] T019 [P] Create `.harness/build.sh` (gate 4: `vite build` in `src/frontend`, then `node .harness/check_bundle_size.mjs`) and `.harness/check_bundle_size.mjs` (gzips the initial JS referenced by `src/frontend/dist/index.html`, fails above `BUNDLE_MAX_KB_GZIP`)
- [X] T020 [P] Create `.harness/e2e.sh` (gate 5) and `scripts/e2e-backend.sh`. `e2e.sh` confirms the DB container accepts connections (clear message if not) and runs `npx playwright test` in `src/frontend`; it does not start the backend, because Playwright `webServer` (T110) owns the backend and frontend processes. `e2e-backend.sh` resolves `Settings.test_database_name`, exports it as `DB_NAME` (an environment variable overrides `.env`), runs `scripts/db-test-init.sh`, then `exec`s uvicorn on port 8000; it never prints `.env` values
- [X] T021 [P] Write the failing test `tests/backend/unit/test_check_function_length.py`: a Python file with a 41-line function fails the check, a 40-line function passes, and the offending function and line count are printed
- [X] T022 [P] Create `.harness/check_function_length.py` (AST scan of `src/backend/app`, limit from `FUNCTION_MAX_LINES`) so T021 passes (depends on T021)
- [X] T023 [P] Create `.harness/redact.sh`: replaces the values of `DB_PASSWORD` (read from `.env` without echoing it) with `<redacted>` in piped output
- [X] T024 [P] Write the failing test `tests/backend/unit/test_harness_summarize.py` with fixture junit and coverage files: `summary.json` lists each failed test with its expected-versus-observed message, each gate's exit code, coverage figures, and the overall result; a run with a failure produces `FAIL` and an all-green run produces `PASS`
- [X] T025 Create `.harness/summarize.py` (reads the results folder, writes `summary.json`, prints the run-table row) so T024 passes (depends on T024)
- [X] T026 [P] Create `.harness/integrity.sh` (gate 0): `shasum -a 256 -c .harness/config/checksums.sha256`; the header comment documents how a legitimate change regenerates the checksum file; the checksummed set includes the lint, type, and secret-scan configuration, so loosening any of them is detected
- [X] T027 Create `.harness/run.sh`: runs gates `integrity`, `lint`, `security`, `test`, `build`, `e2e` in order (continuing after a failure), exports `HARNESS_OUT=evidence/harness-results/<timestamp>`, pipes each gate's output through `redact.sh` into `<gate>.stdout`/`.stderr` with `<gate>.exitcode`, calls `summarize.py`, appends the run-table row to the end of `evidence/harness-log.md`, prints `PASS` or `FAIL`, and exits non-zero on any failure; `--dry-run` writes to a temporary folder and does NOT touch `harness-log.md` (depends on T016-T026)
- [X] T028 Generate `.harness/config/checksums.sha256` with `shasum -a 256` over `.harness/*.sh`, `.harness/*.py`, `.harness/*.mjs`, `.harness/config/thresholds.env`, `.harness/config/gitleaks.toml`, `src/backend/ruff.toml`, `src/backend/mypy.ini`, `src/frontend/eslint.config.js`, and `src/frontend/tsconfig.json` (depends on T015-T027)
- [X] T029 Verify the harness mechanics without recording evidence: `bash .harness/integrity.sh` passes; editing `thresholds.env` makes it fail and restoring it makes it pass again; `bash .harness/run.sh --dry-run` runs every gate on the skeleton and its summary shows the expected PASS/FAIL per gate (the skeleton has no tests yet, so a failing test or build gate is expected and is not a defect) (depends on T028)
- [X] T030 Commit `chore: deterministic harness (gates, thresholds, integrity checksums)`

### Tests first (application foundation)

- [X] T031 [P] Write `tests/backend/unit/test_settings.py`: settings load `DB_NAME`, `DB_USER`, `DB_PASSWORD` from the environment; missing any raises a validation error at construction (fail fast); `DB_HOST` defaults to `localhost`, `DB_PORT` to `1433`; `repr`/`str` of settings and of the database URL never contain the password value; test database name equals `<DB_NAME>_test`; a wildcard in `CORS_ORIGINS` is rejected
- [X] T032 [P] Write `tests/backend/unit/test_architecture.py`: AST-scan `src/backend/app` and fail if `models` imports `repositories|services|api|db`, `repositories` imports `services|api`, `services` imports `api|db`, `core` imports another layer, or any module outside `core/config.py` reads `os.environ`/`os.getenv`
- [X] T033 [P] Write `tests/backend/unit/test_error_handlers.py`: each domain exception maps to its status and `error.code` (`InvalidSeatError` 400 `invalid_seat`, `BusNotFoundError` 404 `bus_not_found`, `UserNotFoundError` 404 `user_not_found`, `SeatAlreadyBookedError` 409 `seat_unavailable`, SQLAlchemy `OperationalError` 503 `service_unavailable`, unexpected `Exception` 500 `internal_error`); every body equals `{"error": {"code": str, "message": str}}`; the 500 and 503 bodies contain no traceback, SQL, host, or file path; request validation errors return 422 `validation_error` in the same shape without echoing the submitted value
- [X] T034 [P] Write `tests/backend/unit/test_startup.py`: with an injected `wait_for_db` that fails twice and then succeeds, `TestClient(create_app(wait_for_db=...))` starts and `GET /api/v1/health/ready` returns 200; with one that always raises, entering the app lifespan raises and no request is served; the `wait_for_database` helper retries a failing probe until its timeout and then raises (fake probe, fake sleep, fake clock)
- [X] T035 [P] Write `tests/backend/contract/test_health.py`: `GET /api/v1/health` returns 200 `{"status": "ok"}` even when the DB dependency is overridden to fail; `GET /api/v1/health/ready` against the test database returns 200 `{"status": "ok"}`; with `get_session` overridden to raise SQLAlchemy `OperationalError`, `GET /api/v1/health/ready` returns 503 with body `{"error": {"code": "service_unavailable", "message": ...}}` that contains no SQL, host, or exception text
- [X] T036 Write `tests/backend/integration/test_schema_and_seed.py` (needs T052): after migration the database has exactly the application tables `buses`, `users`, `bookings` (plus `alembic_version`); inserting a second booking with the same `(bus_id, seat_number)` raises `IntegrityError`; `total_seats` 0 and 61 are rejected by `CHECK (total_seats BETWEEN 1 AND 60)`; `seat_number` 0 is rejected by `CHECK (seat_number >= 1)`; duplicate bus name and user name and blank names rejected; seed yields buses (1 "Bus A" 20, 2 "Bus B" 30, 3 "Bus C" 40), users (1 "Asha", 2 "Ravi", 3 "Meera"), 0 bookings; running seed twice, even after bookings were added, returns the identical state and new booking ids restart at 1
- [X] T037 [P] Write `tests/backend/contract/test_no_secret_leak.py` (NFR-004): with the database password known to the test, trigger a 500 and a 503 and assert neither the response bodies nor the captured log records (`caplog`) contain the password value, the connection URL, or the DB host
- [X] T038 [P] Write `src/frontend/tests/api/client.test.ts`: `request` returns parsed JSON on 2xx; maps error bodies to `ApiError` with `kind` `conflict` (409 / `seat_unavailable`), `invalid` (400, 404, 422), `unavailable` (503, 500, network failure, non-JSON error body)
- [X] T039 Confirm failing: run `T031`-`T038` (pytest and vitest) and verify they fail because the application modules do not exist yet; note the failure summary in the commit message, and stop if any of them passes (a test that cannot fail proves nothing)

### Implementation (backend)

- [X] T040 [P] Implement `src/backend/app/core/config.py`: `Settings` (pydantic-settings, `.env` at repo root, `extra="ignore"`) with required `DB_NAME`, `DB_USER`, `DB_PASSWORD` (`SecretStr`), optional `DB_HOST="localhost"`, `DB_PORT=1433`, `CORS_ORIGINS` (comma list, default `http://localhost:5173`, wildcard rejected), property `test_database_name`, method `database_url(database)` returning a SQLAlchemy `URL`, and cached `get_settings()`; this is the only module allowed to read environment variables
- [X] T041 [P] Implement `src/backend/app/core/errors.py`: base `AppError(code, message)` and `InvalidSeatError`, `BusNotFoundError`, `UserNotFoundError`, `SeatAlreadyBookedError`, each with a fixed `code` (`invalid_seat`, `bus_not_found`, `user_not_found`, `seat_unavailable`)
- [X] T042 [P] Implement `src/backend/app/core/clock.py`: `Clock` Protocol (`now() -> datetime`) and `SystemClock` returning timezone-aware UTC
- [X] T043 [P] Implement `src/backend/app/models/base.py`: SQLAlchemy 2.0 `DeclarativeBase` with a naming convention for constraints and a `UtcDateTime` type (`DATETIME2(3)`, stores naive UTC, returns timezone-aware UTC)
- [X] T044 [P] Implement `src/backend/app/models/bus.py`: table `buses` with `id` `INT IDENTITY(1,1)` primary key; `name` `NVARCHAR(100)` NOT NULL, UNIQUE, non-blank; `total_seats` `INT` NOT NULL, `CHECK (total_seats BETWEEN 1 AND 60)`
- [X] T045 [P] Implement `src/backend/app/models/user.py`: table `users` with `id` `INT IDENTITY(1,1)` primary key; `name` `NVARCHAR(100)` NOT NULL, UNIQUE, non-blank
- [X] T046 Implement `src/backend/app/models/booking.py`: table `bookings` with `id` `INT IDENTITY(1,1)` primary key; `bus_id` `INT` NOT NULL, FK to `buses.id`; `user_id` `INT` NOT NULL, FK to `users.id`; `seat_number` `INT` NOT NULL, `CHECK (seat_number >= 1)`; `booked_at` `DATETIME2(3)` NOT NULL, UTC, set by the server; `UQ_bookings_bus_seat UNIQUE (bus_id, seat_number)`; no index on `user_id` (depends on T043-T045)
- [X] T047 Create `src/backend/alembic.ini` (no connection URL or credentials in it), `src/backend/migrations/env.py` (URL built from `Settings`; target database chosen through `config.attributes["database"]` or `-x database=NAME`), and `src/backend/migrations/versions/0001_create_core_tables.py` creating the three tables, constraints, and index exactly as in data-model.md (depends on T040, T046)
- [X] T048 Implement `src/backend/app/db/session.py`: engine factory for `mssql+pymssql://` with `pool_pre_ping=True`, session factory, `unit_of_work(factory)` and `get_session` (commit when the request succeeds, roll back on any exception), and `wait_for_database(probe=None, *, timeout_seconds=60, interval_seconds=1, sleep, monotonic)` retrying `SELECT 1` (depends on T040)
- [X] T049 Implement `src/backend/app/db/admin.py`: connect to `master` with autocommit and provide `create_database_if_missing(settings, name)` and `drop_and_create_database(settings, name)`; validate `name` against `^[A-Za-z0-9_]+$` and quote it with the dialect's identifier preparer before building the DDL; small CLI (`wait`, `create`, `recreate`) (depends on T048)
- [X] T050 Implement `src/backend/app/db/seed.py` (`python -m app.db.seed [--database NAME]`): `TRUNCATE TABLE bookings`, delete `users` then `buses`, insert buses and users with explicit ids (data in data-model.md "Mock data"); idempotent (depends on T046, T048)
- [X] T051 [P] Create `scripts/db-init.sh` (wait for DB, create the database if missing, `alembic -x database=NAME upgrade head`, run seed; default `DB_NAME`) and `scripts/db-test-init.sh` (same for `<DB_NAME>_test`); both `set -euo pipefail`, never echo `.env` values, executable (depends on T047, T049, T050)
- [X] T052 Create `tests/backend/conftest.py`: session-scoped fixture that asserts the test database name ends in `_test`, drops and recreates it via `db/admin.py`, runs Alembic upgrade programmatically; autouse fixture that runs the seed reset before every test outside `unit/`; fixtures for a session factory, a `FakeClock`, an `app` with `get_session` and `get_clock` overridden, and a `TestClient` (`raise_server_exceptions=False`) (depends on T047, T049, T050)
- [X] T053 [P] Implement `src/backend/app/api/schemas/common.py`: `ErrorBody`, `ErrorResponse`, generic `Page[T]` (`items`, `page`, `page_size`, `total`), `MAX_ID = 2147483647`, and a `page_params` dependency with `page` `ge=1, le=1000000` default 1 and `page_size` `ge=1, le=100` default 20
- [X] T054 Implement `src/backend/app/api/error_handlers.py`: the only place exceptions become HTTP responses; handlers for `AppError` subclasses (status table in T033), `RequestValidationError` (422 `validation_error`, message without submitted values), `OperationalError` and pool timeouts (503, generic text), and a catch-all (500 `internal_error`, traceback logged server-side only) (depends on T041, T053)
- [X] T055 [P] Implement `src/backend/app/api/deps.py` with `SessionDep` (`Depends(get_session, scope="function")` so the commit happens before the response is sent) and `get_clock`; service providers are added by the story phases
- [X] T056 Implement `src/backend/app/api/v1/health.py` (`GET /health` returns `{"status": "ok"}`; `GET /health/ready` runs `SELECT 1`, 503 on failure) and `src/backend/app/api/v1/router.py` aggregating routers under prefix `/api/v1`
- [X] T057 Implement `src/backend/app/main.py`: `create_app(wait_for_db=wait_for_database)` factory (title/version, CORS allow-list from `Settings.CORS_ORIGINS` with no wildcard, handlers from T054, v1 router, stdlib logging that never logs settings values); a `lifespan` handler calls `wait_for_db()` in a worker thread before the app accepts requests, retrying `SELECT 1` for up to 60 s and then raising so the process exits (fail fast) (depends on T048, T054, T056)

### Implementation (frontend)

- [X] T058 [P] Implement `src/frontend/src/api/types.ts` (types mirroring `contracts/openapi.yaml`: `Bus`, `BusDetail`, `Seat`, `SeatStatus`, `User`, `Page<T>`, `BookingCreate`, `Booking`, `BookingResult`, `ErrorResponse`) and `src/frontend/src/api/errors.ts` (`ApiError` with `kind: "conflict" | "invalid" | "unavailable"`, `kindForStatus`, and `describeApiError` mapping to the three user-facing messages of FR-022)
- [X] T059 Implement `src/frontend/src/api/client.ts`: `request<T>(path, options)` over native `fetch`, base URL `import.meta.env.VITE_API_BASE_URL` or `/api/v1`, error mapping per T038 (depends on T058)
- [X] T060 [P] Write the test then implement `src/frontend/src/components/StatusMessage.tsx` and `src/frontend/tests/components/StatusMessage.test.tsx`: variants `loading`, `empty`, `error` (with optional Retry button), `success`, `conflict`; `role="status"` for loading/success/empty and `role="alert"` for error/conflict
- [X] T061 [P] Write the test then implement `src/frontend/src/components/ErrorBoundary.tsx` and `src/frontend/tests/components/ErrorBoundary.test.tsx`: a child that throws renders a readable fallback and does not crash the tree
- [X] T062 [P] Create `src/frontend/src/styles/global.css`: mobile-first base styles, CSS variables, `box-sizing: border-box`, visible focus outline, seat grid and booking bar styles; no `overflow-x: hidden` on `html`/`body` (the layout itself must fit 320 px)
- [X] T063 Checkpoint: create the migrated dev and test databases with `scripts/db-init.sh` and `scripts/db-test-init.sh`; run `.harness/integrity.sh`, `lint.sh`, `security.sh`, and `test.sh` (development runs, not evidence); T031-T038 must pass and lint and security must be clean; then commit `feat: application foundation` and report to the user before starting Phase 3

**Checkpoint**: foundation tests pass; the harness gate scripts run green on the foundation code; foundation committed.

---

## Phase 3: User Story 1 - View a bus and its seats (Priority: P1) MVP

**Goal**: User sees the bus list and, for a chosen bus, every seat marked available or booked (FR-007, FR-008, FR-018, FR-023, FR-024).

**Independent Test**: With seeded data, `GET /api/v1/buses/1` returns 20 available seats; after inserting a booking for seat 5 directly in the test database, seat 5 is `booked`; the UI shows the same.

### Tests for User Story 1 (write first)

- [X] T064 [P] [US1] Write `tests/backend/contract/test_buses.py`: list returns 3 buses with `id`, `name`, `total_seats` (Bus A 20); `page_size=101` and `page=0` return 422 `validation_error`; default `page_size` is 20; detail of bus 1 returns exactly 20 seats numbered 1-20 all `available`; with a booking row for seat 5 only seat 5 is `booked`; bus 99 returns 404 `bus_not_found`; `bus_id=abc` and `bus_id=0` return 422; `bus_id=99999999999999999999` (above 2,147,483,647) returns 422 `validation_error`, not 500; bookings of bus 1 do not affect bus 2
- [X] T065 [P] [US1] Write `tests/backend/unit/test_bus_service.py` with fake in-memory repositories: seats are `1..total_seats` ordered; booked numbers map to `booked`; unknown bus raises `BusNotFoundError`; list returns a page with `total`
- [X] T066 [P] [US1] Write `src/frontend/tests/components/BusList.test.tsx`: renders each bus name and seat count as a link to `/buses/:id`
- [X] T067 [P] [US1] Write `src/frontend/tests/components/SeatGrid.test.tsx`: one control per seat; accessible names like "Seat 5, booked" / "Seat 6, available"; booked seats are `disabled` and show the text "Booked" (not colour alone); available seats are reachable by keyboard Tab and booked ones are skipped
- [X] T068 [P] [US1] Write `src/frontend/tests/pages/BusListPage.test.tsx` and `src/frontend/tests/pages/BusSeatsPage.test.tsx` (viewing): loading, empty, error with working Retry and no partial seat list, "Bus not found." for a 404 and for a malformed id, and the full seat list on success (API client modules mocked with `vi.mock`); shared helpers in `src/frontend/tests/helpers.tsx`
- [X] T069 [US1] Confirm failing: run T064-T068 and verify each fails for the expected reason (404 route missing, module not found); stop if any passes

### Implementation for User Story 1

- [X] T070 [P] [US1] Implement `src/backend/app/repositories/protocols.py` (small role Protocols: `BusReader` with `list_page(page, page_size)`, `count()`, `get(bus_id)`; `BookedSeatReader` with `booked_seat_numbers(bus_id)`) and `src/backend/app/services/types.py` (frozen dataclasses `PageResult`, `BusSummary`, `SeatView`, `BusDetailView`)
- [X] T071 [P] [US1] Implement `src/backend/app/repositories/bus_repository.py` (SQLAlchemy queries, ordered by `id`, parameterised) satisfying `BusReader`
- [X] T072 [P] [US1] Implement `src/backend/app/repositories/booking_repository.py` with `booked_seat_numbers(bus_id)` (uses the `UQ_bookings_bus_seat` index) satisfying `BookedSeatReader`
- [X] T073 [US1] Implement `src/backend/app/services/bus_service.py`: `list_buses`, `get_bus_detail` (derive seats 1..`total_seats` with status), raising `BusNotFoundError`; depends only on the Protocols (depends on T070)
- [X] T074 [P] [US1] Implement `src/backend/app/api/schemas/bus.py`: `BusOut`, `SeatOut` (`status` Literal `available|booked`), `BusDetailOut`, `BusPage` with `from_attributes`
- [X] T075 [US1] Implement `src/backend/app/api/v1/buses.py` (`GET /buses`, `GET /buses/{bus_id}` with `bus_id` `Path(ge=1, le=2147483647)`), add the bus service provider to `src/backend/app/api/deps.py`, and include the router in `src/backend/app/api/v1/router.py` (depends on T071-T074, T053, T056)
- [X] T076 [P] [US1] Implement `src/frontend/src/api/buses.ts` (`listBuses`, `getBus`) and hooks `src/frontend/src/hooks/useAsyncResource.ts`, `useBuses.ts`, `useBusDetail.ts` (state `loading|ready|error`, `refresh()` keeps old data while reloading)
- [X] T077 [P] [US1] Implement `src/frontend/src/components/BusList.tsx` and `src/frontend/src/components/SeatItem.tsx` (button, `aria-pressed` for selected, accessible name, text label and icon per state)
- [X] T078 [US1] Implement `src/frontend/src/components/SeatGrid.tsx` (responsive CSS grid, minimum tap target 44 px, wraps at 320 px) (depends on T077)
- [X] T079 [US1] Implement `src/frontend/src/pages/BusListPage.tsx` and `src/frontend/src/pages/BusSeatsPage.tsx` (read-only: loading, empty, error/retry, not-found, seat grid), `src/frontend/src/App.tsx` (routes `/` and `/buses/:busId`, `React.lazy` pages, `ErrorBoundary`), `src/frontend/src/main.tsx` (depends on T076-T078)
- [X] T080 [US1] Checkpoint: run `.harness/integrity.sh`, `lint.sh`, `security.sh`, `test.sh`, and `build.sh` (development runs); all US1 tests pass and lint, security, and build are clean; commit `feat(us1): view buses and seats`; report to the user

**Checkpoint**: US1 works end to end against the seeded database and is demonstrable alone (quickstart scenarios 1-2).

---

## Phase 4: User Story 4 - Choose the booking user (Priority: P2)

**Goal**: User picks which mock user the booking is for (FR-009, FR-020). Scheduled before US2 because the US2 screen needs the selector; the US2 backend does not depend on it.

**Independent Test**: `GET /api/v1/users` returns 3 users; the UI selector lists them and holds the chosen id.

### Tests for User Story 4 (write first)

- [X] T081 [P] [US4] Write `tests/backend/contract/test_users.py`: list returns Asha, Ravi, Meera with ids 1-3; `page_size=101` and `page=0` return 422; shape matches `User`
- [X] T082 [P] [US4] Write `tests/backend/unit/test_user_service.py` with a fake repository: returns a page with `total`
- [X] T083 [P] [US4] Write `src/frontend/tests/components/UserSelect.test.tsx`: labelled select listing all users with a placeholder option; selecting calls `onChange(userId)` and the placeholder calls `onChange(null)`; error with Retry and empty states
- [X] T084 [US4] Confirm failing: run T081-T083 and verify each fails for the expected reason; stop if any passes

### Implementation for User Story 4

- [X] T085 [P] [US4] Extend `src/backend/app/repositories/protocols.py` with `UserReader` (`list_page`, `count`, `get`) and implement `src/backend/app/repositories/user_repository.py`
- [X] T086 [US4] Implement `src/backend/app/services/user_service.py` (`list_users`) and `src/backend/app/api/schemas/user.py` (`UserOut`, `UserPage`) (depends on T085)
- [X] T087 [US4] Implement `src/backend/app/api/v1/users.py` (`GET /users`), add its provider to `src/backend/app/api/deps.py`, include in `src/backend/app/api/v1/router.py` (depends on T086)
- [X] T088 [P] [US4] Implement `src/frontend/src/api/users.ts`, `src/frontend/src/hooks/useUsers.ts`, and `src/frontend/src/components/UserSelect.tsx`
- [X] T089 [US4] Render `UserSelect` in `src/frontend/src/pages/BusSeatsPage.tsx` holding the selected user id; add a page test to `src/frontend/tests/pages/BusSeatsPage.test.tsx` that choosing "Ravi" keeps Ravi selected (depends on T088)
- [X] T090 [US4] Checkpoint: run `.harness/integrity.sh`, `lint.sh`, `security.sh`, `test.sh`, and `build.sh`; all tests pass; commit `feat(us4): choose the booking user`; report to the user

**Checkpoint**: user selector works (quickstart scenario 6, first half).

---

## Phase 5: User Story 2 - Book one or more seats (Priority: P1)

**Goal**: A user selects 1-6 available seats and confirms; one booking row per seat is stored with a shared UTC booking datetime (FR-010 to FR-013, FR-016, FR-019 to FR-022).

**Independent Test**: As Asha, book seats 3 and 4 on Bus A via `POST /api/v1/bookings`: 201, two rows with bus 1, user 1, one shared `booked_at`; invalid requests are refused and store nothing.

### Tests for User Story 2 (write first)

- [X] T091 [P] [US2] Write `tests/backend/contract/test_bookings_create.py`: body `{"bus_id":1,"user_id":1,"seat_numbers":[3,4]}` returns 201 with two bookings sharing the fake-clock `booked_at` (ISO-8601 UTC), two rows in the table; rejected with no rows stored: empty list 422, duplicate `[3,3]` 422, 7 seats 422, seat 0 and `-1` 422, seat 21 on Bus A 400 `invalid_seat`, unknown bus 404 `bus_not_found`, unknown user 404 `user_not_found`, extra field 422, non-integer or string ids 422; `bus_id`, `user_id`, and a seat number of `99999999999999999999` each 422; seat `2147483647` on Bus A 400 `invalid_seat`; a client-supplied `booked_at` is rejected (extra field); six seats are accepted
- [X] T092 [P] [US2] Write `tests/backend/unit/test_booking_service.py` with fake repositories and `FakeClock`: validates seats against `total_seats` (`InvalidSeatError`), loads bus and user (`*NotFoundError`), passes one timestamp for all rows, returns all created bookings, writes nothing on error
- [X] T093 [P] [US2] Write `tests/backend/unit/test_booking_schema.py`: `BookingCreate` accepts 1 and 6 seats, rejects 0 and 7, duplicates, values below 1, values above 2147483647, string and float values, unknown fields
- [X] T094 [P] [US2] Write `src/frontend/tests/hooks/useSeatSelection.test.ts`: toggle select/deselect, booked seats cannot be selected, selecting a 7th seat is ignored and `limitReached` is true, `clear()` empties selection, seats that become booked drop out of the selection
- [X] T095 [P] [US2] Write `src/frontend/tests/components/BookingBar.test.tsx`: Confirm disabled when no user, no seats, or request in flight; enabled otherwise; shows selected seat numbers, the "choose a user" hint, and the 6-seat limit hint
- [X] T096 [US2] Add booking tests to `src/frontend/tests/pages/BusSeatsPage.booking.test.tsx`: choose user and seats 3, 4, Confirm sends `{bus_id, user_id, seat_numbers: [3,4]}`, shows a progress indication while pending and a success message listing seats 3 and 4, clears the selection, and re-fetches the bus so seats 3 and 4 show "Booked"; Confirm is disabled while the request is pending (a second click sends no second request); a seventh seat cannot be selected; Confirm is disabled without a user or seats; an unconfirmed selection is discarded on reload: select seats 3 and 4, unmount and re-render the page (simulating a reload), then no seat is selected, Confirm is disabled, and `createBookings` was never called
- [X] T097 [US2] Confirm failing: run T091-T096 and verify each fails for the expected reason (route missing, module not found); stop if any passes

### Implementation for User Story 2

- [X] T098 [P] [US2] Implement `src/backend/app/api/schemas/booking.py`: `BookingCreate` (`extra="forbid"`; `bus_id` and `user_id` strict `int` `ge=1, le=2147483647`; `seat_numbers` `list[int]` with `min_length=1`, `max_length=6`, each item strict `ge=1, le=2147483647`, validator rejecting duplicates), `BookingOut` (`id`, `bus_id`, `user_id`, `seat_number`, `booked_at`), `BookingResult` (`bookings`)
- [X] T099 [US2] Extend `src/backend/app/repositories/protocols.py` with `BookingWriter` (`add_many(bus_id, user_id, seat_numbers, booked_at) -> list[Booking]`) and implement `add_many` in `src/backend/app/repositories/booking_repository.py` (insert one row per seat, `flush`; no commit)
- [X] T100 [US2] Implement `src/backend/app/services/booking_service.py`: `book_seats(bus_id, user_id, seat_numbers)` loads bus (`BusNotFoundError`) and user (`UserNotFoundError`), raises `InvalidSeatError` if any seat > `total_seats`, takes one `now()` from the injected `Clock`, calls `add_many`; depends only on Protocols (depends on T092, T099)
- [X] T101 [US2] Implement `src/backend/app/api/v1/bookings.py` (`POST /bookings`, status 201, response `BookingResult`), add the booking service provider to `src/backend/app/api/deps.py`, include in `src/backend/app/api/v1/router.py` (depends on T098, T100)
- [X] T102 [P] [US2] Implement `src/frontend/src/api/bookings.ts` (`createBookings`) and `src/frontend/src/hooks/useSeatSelection.ts` (maximum 6; selection lives only in component state and MUST NOT be written to `localStorage`, `sessionStorage`, or the URL)
- [X] T103 [US2] Implement `src/frontend/src/hooks/useBookSeats.ts` (states `idle|submitting|success|error`, a ref guard against duplicate submits, outcome `success|conflict|failed|ignored`) (depends on T102)
- [X] T104 [P] [US2] Implement `src/frontend/src/components/BookingBar.tsx` and `src/frontend/src/components/BookingFeedback.tsx` (success, conflict, and error messages via `describeApiError`)
- [X] T105 [US2] Make `SeatGrid`/`SeatItem` selectable and wire selection, `BookingBar`, `useBookSeats`, success message, selection clear, and `refresh()` of the bus into `src/frontend/src/pages/BusSeatsPage.tsx` (depends on T089, T103, T104)
- [X] T106 [US2] Checkpoint: run `.harness/integrity.sh`, `lint.sh`, `security.sh`, `test.sh`, and `build.sh`; all tests pass; commit `feat(us2): book seats`; report to the user

**Checkpoint**: booking works through API and UI (quickstart scenarios 3, 5, 6).

---

## Phase 6: User Story 3 - Booked seats are protected and visible after booking (Priority: P1)

**Goal**: No seat is ever double-booked, including under concurrency; a failed request stores nothing; booked seats show as booked after reload (FR-006, FR-014, FR-015, FR-022, FR-023, NFR-003, NFR-005).

**Independent Test**: Book seat 7, then book it again: 409 and still one row; 20 simultaneous requests for one seat give exactly one 201.

### Tests for User Story 3 (write first)

- [X] T107 [P] [US3] Write `tests/backend/integration/test_booking_conflicts.py`: second booking of seat 7 returns 409 `seat_unavailable` and the table is unchanged; request `[8, 9, 7]` with 7 already booked returns 409 and seats 8 and 9 stay available (all-or-nothing); the same seat on Bus B is still bookable after Bus A seat 7 is booked; after each rejected request (409, 400, 404, 422) the bookings table is identical to before; 20 threads each with its own session booking seat 10 yield exactly one 201, nineteen 409, and exactly one row
- [X] T108 [P] [US3] Write `tests/backend/contract/test_conflict_response.py`: the 409 body is `{"error": {"code": "seat_unavailable", "message": ...}}` and contains no SQL text or constraint names
- [X] T109 [P] [US3] Extend `src/frontend/tests/pages/BusSeatsPage.booking.test.tsx`: a 409 from the API shows "Seat no longer available" in an alert, the conflicting seat drops out of the selection, and the bus is re-fetched so that seat shows "Booked"; a 503 or network failure shows "Service unavailable", keeps the user's selection, and shows no success message; a 400/422 shows "Invalid request"
- [X] T110 [P] [US3] Create `src/frontend/playwright.config.ts` (`channel: "chrome-canary"`, `webServer` entries: the backend via `scripts/e2e-backend.sh` (test database) and the Vite dev server, both with `reuseExistingServer: false` so a port clash fails loudly; `globalSetup` runs the seed against the test database) and `src/frontend/e2e/booking-persistence.spec.ts`: choose Bus A, user Asha, select seats 5 and 6, Confirm, success message appears; reload the page; seats 5 and 6 are still "Booked" and disabled; then select seat 8 without confirming and reload: seat 8 is available and not selected, and `GET /api/v1/buses/1` still reports seat 8 `available`
- [X] T111 [US3] Confirm failing: run T107-T110 where they can fail before implementation (the conflict tests fail with an unhandled integrity error); record which tests were already satisfied by US2 code; stop only if the backend conflict tests pass

### Implementation for User Story 3

- [X] T112 [US3] Update `add_many` in `src/backend/app/repositories/booking_repository.py` to catch SQLAlchemy `IntegrityError` on `flush`, roll back the session, and raise `SeatAlreadyBookedError` only when the violation is the unique constraint `UQ_bookings_bus_seat` (SQL Server error 2627 or 2601); re-raise other integrity errors; the service never pre-checks and then inserts
- [X] T113 [US3] Ensure `get_session` in `src/backend/app/db/session.py` rolls back on any exception so nothing from a failed request is committed; verify with T107
- [X] T114 [US3] Update `src/frontend/src/hooks/useBookSeats.ts` and `src/frontend/src/pages/BusSeatsPage.tsx` so a conflict triggers a bus refresh and an alert, other failures keep the selection, and a duplicate submit while in flight is ignored
- [X] T115 [US3] Run T107-T110 (including the Playwright spec) and fix failures in code, never by editing assertions
- [X] T116 [US3] Checkpoint: run `.harness/integrity.sh`, `lint.sh`, `security.sh`, `test.sh`, `build.sh`, and `e2e.sh`; commit `feat(us3): conflict protection and persistence`; report to the user

**Checkpoint**: US1-US4 all work; concurrency guarantee proven; quickstart scenarios 3-8 pass.

---

## Phase 7: Polish and Cross-Cutting Concerns

**Purpose**: Contract, performance, accessibility, usability, documentation, and traceability

- [X] T117 [P] Write `tests/backend/integration/test_performance.py` (marker `perf`): seed 1,000 bookings across 17 buses of 60 seats; after 5 warm-up calls, p95 of 50 `GET /api/v1/buses/{id}` calls under `READ_P95_MS` and p95 of 50 six-seat `POST /api/v1/bookings` calls under `WRITE_P95_MS`, both parsed from `.harness/config/thresholds.env` (no literal numbers in the test); run the perf tests serially and re-run once on a miss before reporting a failure
- [X] T118 [P] Write `tests/backend/contract/test_openapi_contract.py`: the app's generated OpenAPI paths, methods, status codes, and schema property names (and required lists) match `specs/001-seat-booking/contracts/openapi.yaml`; fix the app, not the test or the contract, unless the contract change is approved through the spec artifacts
- [ ] T119 [P] Write `src/frontend/e2e/responsive.spec.ts`: for viewport widths 320, 768, 1280 the bus list and seat page have `document.documentElement.scrollWidth <= innerWidth`
- [ ] T120 [P] Add frontend tests in `src/frontend/tests/`: keyboard-only booking flow (Tab to seat, Space/Enter select, Tab to Confirm), the 6-seat limit message, and an architecture check that `src/components` and `src/pages` contain no `fetch` call
- [ ] T121 [P] Write `src/frontend/e2e/usability.spec.ts` (NFR-007, NFR-008, SC-001, SC-002): from the bus list to a confirmed one-seat booking takes at most 5 interactions (choose bus, choose user, select seat, confirm) and under 30 seconds; the bus list is visible within 2 seconds and the seat list within 2 seconds of choosing a bus
- [ ] T122 Create `scripts/dev.sh` (NFR-011, constitution XI): `set -euo pipefail`; load `.env` without echoing values; make the database available with these checks, in order: (1) Docker daemon: if `docker info` fails, run `colima start` and re-check, failing with a clear message if it still fails; (2) if container `azure-sql-edge` is running (`docker inspect -f '{{.State.Running}}'`) and `DB_HOST:DB_PORT` accepts TCP, print "database already running, reusing it" and change nothing; (3) if it is running but the port does not accept connections yet, wait up to 60 s, then fail with a clear message; (4) if it exists but is stopped, run `docker start azure-sql-edge`; (5) if it does not exist and another process already listens on `DB_PORT`, fail with a message naming the port and do NOT start a second instance; (6) if it does not exist and the port is free, create it with `docker compose up -d` when the plugin is available, otherwise `docker run` with the same image, port, `ACCEPT_EULA=1`, named volume, and health command as `docker-compose.yml`, passing the password via `export MSSQL_SA_PASSWORD="$DB_PASSWORD"` and `-e MSSQL_SA_PASSWORD` so no value appears on the command line. It never stops, removes, or recreates an existing container and never touches other databases on it (for example `mid_dev`). A `--check` flag prints which branch would be taken and exits without acting; use it to verify the branches (never delete the user's container to test branch 6). Then run `scripts/db-init.sh`, start uvicorn (`app.main:create_app --factory`, port 8000) and `npm --prefix src/frontend run dev` (port 5173); on Ctrl-C stop only the processes it started and leave the DB container running
- [ ] T123 [P] Create `README.md` with prerequisites (pyenv, venv, uv, npm), Colima and container notes (Azure SQL Edge is retired but pullable; portable T-SQL; swap path to `mssql/server`), `.env` variable list (names only), `scripts/dev.sh` as the single start command, the commands from `specs/001-seat-booking/quickstart.md`, and how to run `.harness/run.sh`
- [ ] T124 Update `specs/001-seat-booking/quickstart.md` setup and test commands to the uv flow and to run backend tests from `src/backend` (`cd src/backend && pytest`) so they use `src/backend/pyproject.toml`; this is a documentation fix, not a spec change
- [ ] T125 Ask the user to confirm before replacing the hand-started `azure-sql-edge` container with the compose-managed one; if declined, document in `README.md` that the existing container is used as is
- [ ] T126 Verify spec traceability: every FR, NFR, SC, and acceptance scenario in `specs/001-seat-booking/spec.md` maps to at least one named test; fill the "Acceptance traceability" section of `evidence/harness-log.md` with the mapping table; add missing tests rather than reducing criteria
- [X] T135 [P] Add DB-tooling tests (gap found at checkpoints T080-T116: backend branch coverage is 61.1% against the 80% minimum because `app/db/admin.py`, `app/db/seed.py` (`main`), and `app/db/session.py` are only exercised by shell scripts). Write `tests/backend/unit/test_db_tooling.py` (no database needed): `validated_name` accepts letters, digits, and underscores and rejects empty names, spaces, quotes, semicolons, and hyphens; `drop_and_create_database` raises `ValueError` before connecting for any name not ending in `_test` (for example `bus_db`, `mid_dev`); `UtcDateTime` rejects a naive datetime, passes `None` through unchanged, converts an aware datetime to naive UTC on write, and returns UTC-aware on read. Write `tests/backend/integration/test_db_tooling.py` (against the test database only): `unit_of_work` commits on success and rolls back, storing nothing, when the block raises; `get_session` does the same through its generator; `seed.main(["--database", <test database>])` returns 0, prints the seeded counts, and its output contains no secret values; `probe_master` succeeds; `create_database_if_missing` and `drop_and_create_database` work on a scratch database named `<DB_NAME>_toolingscratch_test`, creating it once, being idempotent on a second call, recreating it empty, and dropping it in the fixture teardown; `admin.main` handles `wait`, `create`, and `recreate`. Never touch `bus_db` or `mid_dev`. The code already exists, so confirm each new test can fail (temporarily assert a wrong value, then revert) before relying on it; no test may be skipped, and no threshold or coverage setting may change. Done when `.harness/test.sh` reports backend branch coverage of at least 80%
- [ ] T127 Checkpoint: run every gate script individually (`integrity.sh`, `lint.sh`, `security.sh`, `test.sh`, `build.sh`, `e2e.sh`) as development checks; all must pass; commit `feat: polish, performance and documentation`; report to the user

---

## Phase 8: Harness, Evidence, and Human Review (Principles XII and XIII)

**Purpose**: Preserve the first generation, run the deterministic gates, repair genuine failures, record the decision

- [ ] T128 Preserve the first generated implementation BEFORE any harness run or harness-driven correction: make sure everything is committed, tag it `git tag initial-generation`, and copy `src/` (without `node_modules`, `dist`, caches), `tests/`, `.harness/`, and the approved `spec.md`, `plan.md`, `tasks.md` to `evidence/initial-generation/`; record the commit hash and the spec/task context given to the agent in the "Initial generation and context" section of `evidence/harness-log.md`
- [ ] T129 Run `.harness/run.sh` (first recorded run); confirm a folder appears in `evidence/harness-results/` with per-gate outputs and `summary.json`, and a row was appended to the run table
- [ ] T130 If any gate failed: give the failure evidence (the results folder and `summary.json`) to the coding agent, repair the application code without touching the spec, tests, thresholds, or harness scripts, and re-run `.harness/run.sh` unchanged; log in the "Failure and repair log" section of `evidence/harness-log.md` the evidence supplied, what changed, and the re-run outcome; repeat up to 5 attempts per gate, then stop and escalate to the user (never create artificial failures; if nothing failed, record that no repair was needed)
- [ ] T131 Run every scenario in `specs/001-seat-booking/quickstart.md` against the running stack and record the observed results in the "Quickstart validation" section of `evidence/harness-log.md`
- [ ] T132 Run `/speckit-converge`; record the result in the "Convergence results" section of `evidence/harness-log.md` tasks test-first, then re-run `.harness/run.sh`
- [ ] T133 Copy the final `src/` and `tests/` to `evidence/final-generation/`; confirm `gitleaks dir` and `gitleaks git` (with `.harness/config/gitleaks.toml`) report nothing for the project and `evidence/`; commit `chore: final generation and evidence`; draft the known limitations (for example `sa` account use, retired Azure SQL Edge image, no authentication) and a note on every unplanned helper file under the "Final decision" heading of `evidence/harness-log.md` (the human confirms or edits them in T134)
- [ ] T134 Human review: the user records the final ACCEPT or REJECT decision with justification in the "Final decision" section of `evidence/harness-log.md` (the agent MUST NOT write this decision)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: T001 (human gate) first; T002 after APPROVED; the rest after T002
- **Phase 2 Foundational**: after Setup; blocks all stories. The harness (T015-T030) comes before any application code
- **US1 (Phase 3)**: after Foundational
- **US4 (Phase 4)**: after Foundational; backend independent of US1, UI work (T089) needs the US1 page (T079)
- **US2 (Phase 5)**: backend after Foundational and US1 repositories (T070-T072); UI after US1 (T079) and US4 (T089)
- **US3 (Phase 6)**: after US2 (it hardens the booking path)
- **Polish (Phase 7)**: after US1-US4
- **Phase 8**: after Polish; T128 must precede T129

### Why US4 (P2) runs before US2 (P1)

The booking screen needs a user selector, so the selector (US4) is built first even though its priority is lower. The US2 backend is still independently testable without it.

### Within Each Story

- Tests first, then "confirm failing", then protocols, repositories, services, schemas, routes; frontend api, hooks, components, pages
- Never edit tests to make them pass

### Task-level dependencies (key)

- T036 needs T052; T052 needs T047, T049, T050
- T022 needs T021; T025 needs T024; T027 needs T016-T026; T028 needs T015-T027; T029 needs T028
- T075 needs T071-T074; T101 needs T098, T100; T105 needs T089, T103, T104
- T129 needs T128
- T127 needs T135 (the branch-coverage minimum cannot be met without the DB-tooling tests)

## Parallel Examples

```text
# Setup
T003, T004, T008, T009, T010, T011, T012, T013, T014 in parallel after T007

# Harness
T015, T016, T017, T018, T019, T020, T021, T023, T024, T026 in parallel; then T022, T025, T027, T028, T029

# Foundational tests and core modules
T031, T032, T033, T034, T035, T037, T038 in parallel; T040, T041, T042, T043, T044, T045 in parallel

# User Story 1
Tests: T064, T065, T066, T067, T068 in parallel
Implementation: T070, T071, T072, T074, T076, T077 in parallel; then T073, T075, T078, T079

# User Story 2
Tests: T091, T092, T093, T094, T095 in parallel
Implementation: T098, T102, T104 in parallel; then T099, T100, T101, T103, T105
```

## Implementation Strategy

### Approval first, then MVP

1. T001 approval gate; stop until APPROVED
2. Phase 1 and Phase 2 (harness first); run the harness mechanics check (T029)
3. Phase 3 (US1); stop and validate quickstart scenarios 1-2

### Incremental Delivery

1. Setup + Foundational (with harness) -> checkpoint
2. US1 (view) -> checkpoint
3. US4 (user selector) -> checkpoint
4. US2 (booking) -> checkpoint; the feature is now usable
5. US3 (conflict protection, persistence e2e) -> checkpoint
6. Polish -> snapshot (T128) -> harness (T129) -> repair -> converge -> human decision

### Evidence rule

Do not run `.harness/run.sh` (T129) before the initial-generation snapshot (T128). Per-task test runs and gate-script runs during development are allowed and are not harness executions.

## Notes

- [P] tasks touch different files and have no dependency on an incomplete task
- Commit after each checkpoint with a conventional message; never commit `.env`
- Constraints quoted in T044-T046 and T098 are verbatim from data-model.md and the spec; do not alter them
