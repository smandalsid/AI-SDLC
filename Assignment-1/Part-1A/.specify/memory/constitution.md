<!--
Sync Impact Report (temporary; remove before commit)
- Version change: 1.4.0 -> 1.4.1 (PATCH). Reason: analysis of feature 002 found that Principle XIII names the tag
  `initial-generation`, which feature 001 already owns, so a later feature could not comply literally.
  Clarified Principle XIII: for a later feature whose tag name is taken, the tag is
  `<NNN>-initial-generation` and the earlier feature's evidence is archived under `evidence/<NNN>-<name>/`
  first. Wording only; no principle added, removed, or redefined; feature 001 evidence is not re-written.
  Impact: specs/002-user-authentication/{plan,tasks}.md cite v1.4.1. The mock-user exemption sentence of
  Principle VII is unchanged and is to be retired by a separate amendment after feature 002 is accepted.
- Earlier: 1.3.1 -> 1.4.0 (MINOR). Reason: genuine failures seen while developing (task test runs, phase
  checkpoints, gate script runs) were not captured in the failure-and-repair log, which only covered recorded
  runs. Principle XII gains a failure-logging rule, the Deterministic Harness & Evidence section and the
  Development Workflow gain matching text, and the Measurable Engineering Constraints table gains a row.
  No principle added or removed. Applies from the next feature; feature 001 was closed with ACCEPT under
  1.3.1 and its evidence is not re-written. Templates re-checked: tasks-template.md updated in the same change.
- Earlier: 1.3.0 -> 1.3.1 (PATCH). Reason: analysis found numeric thresholds and lint/type/secret-scan
  configuration outside the protected harness configuration. Clarified Principle XII (numeric thresholds
  are injected by the gate scripts; the integrity checksum covers the lint, type, and secret-scan config)
  and Principle XIII (the agent may not edit those files). No principle added or removed.
- Earlier: 1.2.0 -> 1.3.0 (MINOR). Reason: the first implementation attempt never reached the
  harness (harness tasks were last, no approval gate, no guardrails against running ahead).
- Modified principles: V (tests MUST be written first and observed failing); XII renamed
  "Spec-Driven, Harness-Gated Development" -> "Deterministic Harness Built First" (harness before any
  application code, thresholds config, integrity gate, evidence capture, bounded repair).
- Added principles: XIII Agent Guardrails and Human Approval (approval gate, no running ahead,
  initial-generation snapshot, milestone commits).
- Added sections: Technology & Environment Constraints (Python 3.12 via pyenv, root .venv, uv + uv.lock).
- Changed sections: Measurable Engineering Constraints (+4 rows), Deterministic Harness & Evidence,
  Development Workflow & Quality Gates, Governance (NON-NEGOTIABLE list).
- Removed sections: none.
- Templates/artifacts to re-check: specs/001-seat-booking/plan.md and tasks.md (updated in the same change).
- Earlier: 1.1.0 -> 1.2.0 (Principle VII: mock-user features exempt from authentication until a
  dedicated authentication iteration); 1.0.0 -> 1.1.0 (Principle XI: azure-sql-edge image);
  (unratified template) -> 1.0.0.
- Follow-up TODOs: none.
-->

# Bus Booking Platform Constitution

## Core Principles

### I. SOLID, Separation of Concerns, Modularity (NON-NEGOTIABLE)

The codebase MUST follow SOLID strictly and be organised in layers with one-way dependencies:

- Backend layers: `api` (FastAPI routers, request/response schemas only) -> `services`
  (business rules) -> `repositories` (all SQL/ORM access) -> `models`. A layer MUST NOT import
  from a layer above it.
- Routers MUST NOT contain business logic or database queries; services MUST NOT build HTTP
  responses; repositories MUST NOT contain business rules.
- Services MUST depend on abstractions (`typing.Protocol` / ABC) and receive them through
  FastAPI dependency injection (`Depends`), never by instantiating concrete classes inline.
- Frontend MUST separate presentational components, hooks (state/data fetching), and an API
  client module. Components MUST NOT call `fetch`/`axios` directly.
- Each module MUST have a single reason to change (SRP); extension MUST be by adding code, not
  editing stable modules (OCP); implementations MUST be substitutable for their abstractions (LSP);
  interfaces MUST be small and role-specific (ISP).

Rationale: strict layering keeps the codebase simple to reason about, testable in isolation, and
cheap to change.

### II. Input Validation at Every Boundary

- Every API request body, query parameter, and path parameter MUST be validated by a Pydantic
  model with explicit types, length limits, ranges, and formats. Unknown fields MUST be rejected
  (`extra="forbid"`).
- Frontend forms MUST validate before submit; frontend validation is a usability aid only and
  MUST NOT replace backend validation.
- All database access MUST use parameterised queries or the ORM; string-built SQL is forbidden.
- Invalid input MUST return HTTP 422 (schema) or 400 (business rule) with a machine-readable
  error body, and MUST NOT reach the service or repository layer.

### III. Strict Type Hinting

- All Python functions, methods, and class attributes MUST be fully annotated; `mypy --strict`
  MUST report zero errors. `Any` and `# type: ignore` are forbidden unless accompanied by a
  one-line justification comment.
- Frontend MUST be TypeScript with `"strict": true`; `any` is forbidden; `tsc --noEmit` MUST report
  zero errors.
- API request/response types MUST be defined once in the backend schemas, and frontend types
  MUST mirror them exactly.

### IV. Explicit, Consistent Error Handling

- Domain errors MUST be raised as typed exceptions (e.g. `SeatAlreadyBookedError`) from services
  and translated to HTTP responses in a single centralised exception-handler module.
- Bare `except:` and swallowed exceptions are forbidden. Unexpected errors MUST return a generic
  HTTP 500 body and MUST NOT leak stack traces, SQL, or internal paths to clients.
- All error responses MUST share one JSON shape: `{"error": {"code": str, "message": str}}`.
- The frontend MUST render a user-visible message for every failed request and MUST provide an
  error boundary for rendering failures.

### V. Test Coverage Across the Codebase (NON-NEGOTIABLE)

- Tests MUST be written first from the approved acceptance criteria and MUST be observed failing
  before the code that satisfies them is written (red -> green -> refactor). They MUST include
  unit tests (services, validators, components, hooks) and contract/integration
  tests (every API endpoint, success and failure paths, against the real SQL Server container or
  an equivalent transactional test database).
- Coverage minimums are defined in "Measurable Engineering Constraints" and are enforced by the
  harness; they MUST NOT be lowered.
- Every bug fix MUST add a regression test that fails before the fix.

### VI. Secrets Never in Source (NON-NEGOTIABLE)

- Secrets (DB password, JWT signing key, API keys) MUST exist only in `.env` (local) or the
  deployment secret store. They MUST NOT appear in source code, tests, fixtures, Dockerfiles,
  compose files, logs, evidence files, or the harness log.
- `.env` MUST be listed in `.gitignore` and MUST NOT be committed. A committed `.env.example`
  MUST list every variable name with placeholder values only.
- `.env` already provides `DB_NAME`, `DB_USER`, `DB_PASSWORD`; additional variables (e.g.
  `DB_HOST`, `DB_PORT`, `JWT_SECRET`) MUST be added there and loaded through a single typed
  settings module (`pydantic-settings`). Application code MUST NOT read `os.environ` elsewhere.
- The application MUST fail fast at startup if a required variable is missing.
- Coding agents MUST NOT print, copy, or echo secret values into any artifact or conversation.

### VII. Security by Default

- Passwords MUST be stored only as salted hashes (bcrypt or argon2); authentication MUST use
  short-lived signed tokens; protected endpoints MUST enforce authorisation server-side.
- CORS MUST allow only configured origins; wildcard origins are forbidden outside local
  development.
- Dependencies MUST be pinned; the SAST and dependency audit gates in the harness MUST pass.
- Booking operations MUST be safe under concurrency: a seat on a trip MUST NOT be double-booked,
  enforced by a database constraint in addition to service-level checks.
- Features that use mock users and expose no protected endpoints are exempt from the
  authentication and authorisation rules above until an authentication feature is specified;
  that feature is scheduled as a separate iteration and MUST be delivered before any real use.

### VIII. Simple, Minimal Data Model

- The schema MUST contain only entities required by approved specifications (expected core:
  User, Route, Bus, Trip, Booking; seats are derived from the Bus capacity unless a spec proves
  otherwise).
- Every table MUST have a surrogate primary key, explicit foreign keys, appropriate indexes
  for documented query paths, and NOT NULL/unique/check constraints reflecting the rules.
- Schema changes MUST be made only through versioned migrations (Alembic); manual schema edits
  are forbidden. Adding a table or column MUST be justified in the spec or plan.

### IX. Scalable and Simple Architecture

- The backend MUST be stateless (no in-process session or booking state) so it can be scaled
  horizontally; all state lives in the database.
- List endpoints MUST be paginated with a documented maximum page size.
- Prefer the simplest solution that satisfies the spec (YAGNI). New dependencies, services, or
  abstractions MUST be justified in the plan's complexity section.
- The API MUST be versioned under a path prefix (`/api/v1`) and documented via the generated
  OpenAPI schema.

### X. Simple, Responsive, Lightweight UI

- The frontend MUST be React + Vite + TypeScript and MUST work from 320 px to 1920 px viewport
  widths without horizontal scrolling (mobile-first CSS).
- No heavy UI frameworks or large dependencies without plan justification; routes MUST be
  code-split. Size budgets are in "Measurable Engineering Constraints".
- Interactive elements MUST be keyboard-accessible and labelled; loading, empty, and error
  states MUST be implemented for every data-driven view.

### XI. Reproducible Local Environment

- The database MUST be Azure SQL Edge (`mcr.microsoft.com/azure-sql-edge` image; T-SQL compatible
  with Azure SQL) running in Docker on Colima, defined in a `docker-compose.yml` that reads
  credentials from `.env` and never hard-codes them. Application code MUST use only portable
  T-SQL features so the engine can be swapped for `mcr.microsoft.com/mssql/server` if the
  Azure SQL Edge image is withdrawn.
- The database service MUST have a healthcheck (the image ships no `sqlcmd`, so a TCP probe is
  acceptable); the backend MUST retry its connection at startup and MUST NOT report ready until
  the database accepts queries.
- Azure SQL Edge runs natively on Apple Silicon (arm64); no emulation flags are required.
  Setup steps MUST be documented in the README.
- If the corporate TLS proxy breaks image pulls, the corporate CA MUST be installed in the Colima
  VM rather than disabling TLS verification.

### XII. Deterministic Harness Built First (NON-NEGOTIABLE)

- A harness under `.harness/` MUST exist and be runnable with one command (`.harness/run.sh`)
  before any application code is written. Harness tasks belong to the Foundational phase, never to
  the last phase, and every phase checkpoint MUST be verified with the gate scripts.
- Gates, in order, each with an unambiguous pass/fail result: (0) integrity, (1) syntax and lint,
  (2) security/SAST and dependency audit, (3) unit and contract tests, plus the project-specific
  build-size and end-to-end gates. Code is accepted only when every gate passes.
- All numeric thresholds live in `.harness/config/thresholds.env`; the gate scripts inject them into
  the tools (for example the complexity and function-length limits), and tool configuration files
  carry rule selection only. The harness scripts, the thresholds, and the lint, type, and
  secret-scan configuration (`ruff.toml`, `mypy.ini`, `eslint.config.js`, `tsconfig.json`,
  `gitleaks.toml`) are protected by `.harness/config/checksums.sha256`, verified by the integrity
  gate; lowering a threshold requires a constitution amendment, and any change to a protected file
  requires a regenerated checksum file that is visible in review.
- On every run the runner MUST record stdout, stderr, exit codes, the junit and coverage reports,
  and a `summary.json` that names each failed rule or test with its expected and observed
  behaviour, under `evidence/harness-results/<timestamp>/`, and MUST append one row to the run
  table at the end of `evidence/harness-log.md`.
- Individual gate scripts MAY be run while developing; only runs made through `.harness/run.sh`
  count as evidence, and the first such run happens only after the initial-generation snapshot
  (Principle XIII).
- Self-healing: failure evidence is fed to the coding agent, the implementation is repaired, and
  the same gates are rerun unchanged. After 5 failed attempts at the same gate the agent MUST stop
  and escalate to a human.
- **Failure logging**: every genuine, unexpected failure MUST be entered in the failure-and-repair
  log of `evidence/harness-log.md` when it occurs, whether it appears in a task's test run, at a
  phase checkpoint, in a gate script run, or in a recorded run. A failure is unexpected when a test
  or gate that should pass does not (a regression, a failed gate, a missed threshold). Tests written
  first that fail as intended (Principle V) are not repair events; their failure summary belongs in
  the commit message. Each entry states the failing gate or test with its evidence, the expected
  and observed behaviour, the change made (commit and files), and the outcome of re-running the
  same checks unchanged. The entry is written no later than the commit that contains the fix.
  Failures MUST NOT be created to fill the log, and a phase with no unexpected failure is logged
  as "no repair needed".

### XIII. Agent Guardrails and Human Approval (NON-NEGOTIABLE)

- **Approval gate**: implementation MUST NOT start until a human has recorded `APPROVED`, their
  name, and the date for `spec.md`, `plan.md`, and `tasks.md` in the Approval section of
  `evidence/harness-log.md`. This is task T001; the agent MUST stop and wait for it.
- The coding agent MUST receive the approved specification context, this constitution, and the
  relevant tasks before generating code.
- Acceptance criteria MUST be written so each yields a binary (pass/fail) test: stated as
  Given/When/Then with concrete inputs, status codes, and field values. Vague criteria
  ("fast", "user-friendly") MUST be quantified or rejected at spec review.
- The coding agent MUST NOT: weaken or delete acceptance criteria; remove, skip, or loosen failing
  tests or assertions; disable or relax lint, type, security, or coverage checks; edit
  `.harness/config/` or the protected lint, type, and secret-scan configuration files; expose
  secrets; bypass the harness; or hand-edit recorded harness results to obtain a PASS.
- **No running ahead**: the agent MUST implement one phase at a time, stop at each phase
  checkpoint to report completed tasks and gate results, and halt on the first failing
  non-parallel task. Completed tasks are marked `[X]` only after their tests pass.
- **First generation preserved**: after the last implementation task and before the first
  `.harness/run.sh`, the code MUST be committed and tagged `initial-generation` and copied to
  `evidence/initial-generation/`; the repaired version goes to `evidence/final-generation/`. For a
  later feature whose tag name is already taken, the tag is `<NNN>-initial-generation` (for example
  `002-initial-generation`) and the earlier feature's evidence is first archived, unedited, under
  `evidence/<NNN>-<name>/`.
- A legitimate specification change MUST be made through the SDD artifacts (spec -> plan ->
  tasks), committed, and documented in `evidence/harness-log.md`.
- The final ACCEPT or REJECT decision, with known limitations and justification, is recorded by a
  human; the agent MUST NOT write it.

## Technology & Environment Constraints

- **Python**: 3.12 selected with `pyenv` (pinned in `.python-version` containing `3.12`).
- **Virtual environment**: `python3.12 -m venv .venv` at the repository root; every Python
  dependency install MUST target this `.venv` and MUST NOT be installed globally.
- **Dependency management**: `uv` is the only Python dependency tool. Dependencies are declared in
  `src/backend/pyproject.toml`, locked in `src/backend/uv.lock` (committed), and installed with
  `uv sync --active` (or `uv pip install` with `VIRTUAL_ENV=.venv`). `requirements.txt` is not a
  source of truth.
- **Frontend**: Vite + React + TypeScript (strict); `npm` with a committed lockfile.
- **Repository layout**: `src/backend`, `src/frontend`, `tests/backend`, `src/frontend/tests`,
  `.harness/`, `evidence/`, `specs/`; `.venv/`, `node_modules/`, build outputs and caches are
  excluded through `.gitignore`.

## Measurable Engineering Constraints

Each constraint is binary and is verified by the harness or a named tool. Numeric thresholds are
stored in `.harness/config/thresholds.env`, injected into the tools by the gate scripts, and MUST
NOT be lowered without a constitution amendment.

| Area | Constraint | Verified by |
|------|-----------|-------------|
| Backend lint | `ruff check` and `ruff format --check`: 0 violations | Lint gate |
| Backend types | `mypy --strict`: 0 errors | Lint gate |
| Frontend lint/types | `eslint --max-warnings 0` and `tsc --noEmit`: 0 issues | Lint gate |
| Complexity | Cyclomatic complexity <= 10 per function (Ruff `C901`); function <= 40 lines | Lint gate |
| Backend coverage | Line coverage >= 85% and branch coverage >= 80% (`pytest --cov`) | Test gate |
| Frontend coverage | Line coverage >= 80% (Vitest) | Test gate |
| Endpoint tests | 100% of endpoints have >= 1 success and >= 1 failure test | Contract tests |
| Backend SAST | `bandit -ll`: 0 medium/high findings | Security gate |
| Dependency audit | `pip-audit` and `npm audit --audit-level=high`: 0 findings | Security gate |
| Secret scan | 0 secrets detected in tracked files and evidence (e.g. `gitleaks`) | Security gate |
| API latency | p95 <= 300 ms for read endpoints with a 1,000-row dataset on local Docker | Performance test |
| Pagination | Default page size 20; max 100; larger values return 422 | Contract tests |
| Frontend size | Initial JS <= 200 KB gzipped per route; production build succeeds | Build gate |
| Responsiveness | No horizontal overflow at 320, 768, 1280 px widths | UI test |
| Data integrity | Concurrent booking of one seat: exactly 1 succeeds, others get HTTP 409 | Integration test |
| Reproducibility | Fresh clone + `.env` + one documented command starts DB, API, and UI | Documented check |
| Skipped tests | 0 skipped or xfail tests without a documented reason | Test gate |
| Harness integrity | `.harness/` scripts and thresholds match `.harness/config/checksums.sha256` | Integrity gate |
| Traceability | Every FR, NFR, and acceptance scenario maps to >= 1 automated test (table in `harness-log.md`) | Review |
| Repair bound | <= 5 repair attempts per gate before human escalation | Process |
| Failure log | Every unexpected failure (task test run, checkpoint, gate script, recorded run) is logged with evidence, fix, and re-run outcome | Review |

## Deterministic Harness & Evidence

The harness is the single entry point `.harness/run.sh` (see Principle XII). It executes all gates
in order, continues after a failure to collect all evidence, and exits non-zero if any gate failed:

0. **Integrity Guard**: checksums of `.harness/` scripts and thresholds.
1. **Syntax & Lint Guard**: Ruff, mypy, ESLint, tsc. Unambiguous PASS/FAIL per tool.
2. **Security / SAST Guard**: Bandit, pip-audit, npm audit, secret scan.
3. **Unit & Contract Tests**: pytest and Vitest, with assertions derived from the approved
   acceptance criteria; all mandatory tests MUST pass, and coverage thresholds MUST be met.
   Build-size and end-to-end checks run as further gates of the same runner.
4. **Feedback Capture**: for each failure, record stdout/stderr, the failed test or rule,
   the expected behaviour, and the observed behaviour (secrets redacted) in `summary.json`.
5. **Self-Healing**: feed the captured failure evidence to the coding agent, repair the
   implementation, and rerun the same harness gates unchanged.
6. **Human Review**: record a final ACCEPT or REJECT decision, known limitations, and
   justification after the automated result.

Harness output MUST be generated by the runner, never typed by hand. Genuine failure-and-repair
cycles MUST be logged, including those first seen in a task's test run or a gate script run between
recorded runs (Principle XII, Failure logging); failures MUST NOT be manufactured.

Required repository layout (names may vary only where tooling requires):

```text
.specify/ and specs/        Spec Kit artifacts (constitution, spec, plan, tasks)
src/                        backend and frontend application code
tests/                      unit, contract, and integration tests
.harness/                   gate scripts, runner, summariser
  config/thresholds.env     all numeric thresholds
  config/checksums.sha256   integrity checksums of the harness
evidence/
  initial-generation/       first generated implementation, preserved unmodified
  final-generation/         implementation after harness-driven repair
  harness-results/          runner-generated outputs per execution
  harness-log.md            chronological record (see below)
```

`evidence/harness-log.md` MUST contain, in this order: the human Approval section; the initial
generation and the task/spec context given; the failure-and-repair log (failure evidence supplied
to the agent, what changed, and whether the same checks passed on re-execution); quickstart
validation; convergence results; the acceptance traceability table; the final human ACCEPT/REJECT
decision with known limitations and justification; and, last, the run table that the runner
appends to.

## Development Workflow & Quality Gates

- Workflow order: constitution -> specify -> clarify -> plan -> tasks -> analyze -> **human approval**
  -> implement (phase by phase) -> snapshot of the first generation -> harness -> repair ->
  converge -> human decision.
- A human MUST approve the spec, plan, and tasks before `/speckit-implement` (Principle XIII).
- Tests derived from acceptance criteria MUST exist and fail before the corresponding
  implementation is written (red -> green).
- After each task, its tests are run; an unexpected failure is logged in the failure-and-repair log
  before the task is marked `[X]` (Principle XII, Failure logging), so no failure seen between
  recorded runs is lost.
- A change is accepted only when every harness gate passes on the final code and a human records
  ACCEPT. A partial PASS is a REJECT.
- Run `/speckit-analyze` before implementation and `/speckit-converge` after it; gaps MUST become
  new tasks or spec changes, not silent code changes.
- Commits MUST be small and use conventional messages (`feat:`, `fix:`, `test:`, `docs:`,
  `chore:`). Milestones MUST be committed: approved artifacts, foundation with harness, each user
  story, the `initial-generation` tag, each repair, and the final generation.
- Commits MUST NOT contain `.env`, credentials, or generated harness output edited by hand.
- Code comments MUST explain intent that code cannot show; they MUST NOT restate the code.
- A `README.md` MUST document setup (pyenv, venv, uv, npm), how to start everything, and how to run
  the harness, with copy-pasteable commands.
- Pull requests/reviews MUST verify compliance with every principle above.

## Governance

This constitution supersedes all other practices for this project. Amendments MUST be made by
editing this file, stating the reason, the version bump, and any impact on existing artifacts;
dependent specs, plans, and tasks MUST be re-checked after an amendment.

Versioning follows semantic versioning: MAJOR for removing or redefining a principle in a
backward-incompatible way; MINOR for adding a principle or materially expanding guidance; PATCH
for clarifications and wording fixes.

Compliance MUST be reviewed at plan time (a Constitution Check in `plan.md`), at `analyze`
time, and at human review. Any violation MUST be fixed or explicitly justified in the plan's
complexity-tracking table before implementation proceeds. Constraints marked NON-NEGOTIABLE
(I, V, VI, XII, XIII) cannot be waived.

**Version**: 1.4.1 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-03
