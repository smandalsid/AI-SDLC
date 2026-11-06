<!--
Sync Impact Report: 1.0.1 -> 1.0.2 (PATCH, requested by the human 2026-11-06).
Reason: the project folder `assignment_2/` was moved to `Assignment-1/Part-1B/`. Every `assignment_2/` in this
file and in specs/ now means the Part-1B folder; the scope rule applies to that folder. No limit or rule changed.
Impact: none; the scope gate (`git rev-parse --show-prefix`) already follows the folder.

Sync Impact Report: 1.0.0 -> 1.0.1 (PATCH, human-approved 2026-11-06, recorded in evidence/harness-log.md).
Reason: a tag named `initial-generation` already exists in the shared repository, and the evidence
redaction scan flags the secret-pattern definitions in plain-text copies. The tag is now
`assignment-2-initial-generation` and snapshots may be archives. No limit or NON-NEGOTIABLE rule changed.
Impact: plan.md Constitution Check row XII (tag name).
-->
# Natural-Language Reminder Agent Constitution

The Natural-Language Reminder Agent is a small AI application. Its LLM behaviour is
non-deterministic and is governed by exactly one evaluation harness. Every rule below is a
testable MUST / MUST NOT; a rule that cannot be checked by the harness, a test, or a
named command is a defect in this constitution.

## Core Principles

### I. Spec-Driven Only (NON-NEGOTIABLE)

- Implementation MUST follow the sequence: constitution -> specify -> clarify -> plan ->
  tasks -> analyze -> human approval -> implement (phase by phase) -> converge.
- Code MUST NOT be produced from a single "build the app" prompt.
- An ambiguity discovered later MUST be fixed in the upstream Spec Kit artifact
  (spec -> plan -> tasks), committed, and recorded in `evidence/harness-log.md`.
- Gaps found by `/speckit-analyze` or `/speckit-converge` MUST become new tasks or spec
  changes, never silent code changes.
- The coding agent MUST NOT change the spec, acceptance criteria, or thresholds to make a
  check pass.

Rationale: a passing check is only meaningful if the target it measures was fixed first.

### II. Non-Determinism Is Made Testable

The spec MUST define all of the following before the first evaluation:

- An output schema contract.
- Structural invariants.
- Behavioural properties that do not depend on exact output text.
- Safety/guardrail rules.
- An evaluation threshold and its scoring formula.

Every eval case MUST trace to at least one requirement ID (`FR-`, `INV-`, `GR-`, or `AC-`).
An eval case with no requirement ID MUST fail the traceability check.

Acceptance criteria MUST be written in Given/When/Then form with concrete inputs, status
codes, and field values, so each yields a binary pass/fail test. Vague terms ("fast",
"user-friendly") MUST be quantified or rejected at spec review.

Rationale: LLM output varies between runs, so correctness is defined by contracts and
properties, not by exact strings.

### III. Harness Built First (NON-NEGOTIABLE)

- The harness (`.harness/`) MUST exist and be runnable with one command (`.harness/run.sh`)
  before any application code is written. Harness tasks MUST belong to the Foundational
  phase, never the last phase.
- Task T001 MUST be a human APPROVED gate (see Principle XII) recorded in
  `evidence/harness-log.md`.
- The agent MUST pause at every phase checkpoint and MUST NOT start a phase that has not
  been approved. The Foundational checkpoint MUST be approved by a human before any
  application code is written.
- One milestone commit MUST be made per phase.

Rationale: a harness written after the code can be shaped to fit the code.

### IV. One Evaluation Harness, Three Layers

A single runner, `.harness/run.sh`, MUST execute all three layers:

1. Layer 1: structural/schema validation.
2. Layer 2: deterministic invariant and property checks.
3. Layer 3: semantic/quality scoring (ground-truth comparison, token/embedding similarity,
   or rubric).

- An LLM judge MAY be used in Layer 3 only. It MUST NOT replace or override Layer 1 or
  Layer 2 results.
- The runner MUST output exactly one of PASS, FAIL, or INVALID, computed against the
  threshold declared in the spec.
- The runner MUST report per-layer and per-category metrics.
- A second, parallel evaluation harness MUST NOT exist.

### V. Harness Protection (NON-NEGOTIABLE)

The agent MUST NOT:

- delete or weaken eval cases, acceptance criteria, tests, or assertions;
- skip, xfail, or loosen a failing test;
- change expected results without a spec revision;
- lower a declared threshold;
- disable or relax a guardrail, lint rule, type check, coverage check, or security check;
- edit `.harness/config/` or the protected lint/type/secret-scan configuration files;
- hand-edit recorded results;
- bypass the harness or skip a mandatory gate.

Further rules:

- Numeric thresholds MUST be stored in `.harness/config/thresholds.env`, injected into the
  tools by the gate scripts, and MUST NOT be hard-coded elsewhere. Tool configuration files
  carry rule selection only.
- `.harness/config/checksums.sha256` MUST cover: the harness scripts, the thresholds file,
  `evals/dataset.json`, the output schema, and the lint/type/secret-scan configuration
  (`ruff.toml`, `mypy.ini`, `gitleaks.toml`, and equivalents).
- Any change to a protected file MUST come with a regenerated checksum file that is visible
  in review. Lowering a threshold MUST require a constitution amendment.
- The integrity gate MUST run first. A checksum mismatch MUST fail the run before any other
  check executes.

### VI. Service Failures Are Not Application Failures

- LLM/runtime errors MUST be classified `INFRA_ERROR`. This covers session errors, JSON-RPC
  errors, auth failures, timeouts, rate/usage-limit errors, and runtime download or startup
  failures.
- An `INFRA_ERROR` case MUST be retried with bounded backoff, MUST be reported separately,
  and MUST be excluded from the quality score.
- A run where more than 10% of cases are `INFRA_ERROR` MUST be reported INVALID, never PASS
  or FAIL.
- The runner MUST support `--mode live|replay`. Replay MUST use redacted recorded responses
  and is for fast iteration and unit tests only.
- ONLY a `live` run MAY produce the final `eval-results.json` and the ACCEPT decision.

### VII. Secrets Never In Source (NON-NEGOTIABLE)

- Tokens MUST exist only in `.env`, which MUST be gitignored.
- A committed `.env.example` MUST list every variable name with placeholder values only.
- Configuration MUST load through one typed settings module (`pydantic-settings`). Application
  code MUST NOT read `os.environ` anywhere else. The app MUST fail fast at startup if a
  required variable is missing.
- Secrets MUST NOT appear in code, tests, fixtures, recorded responses, logs, evidence, or
  `harness-log.md`.
- The harness MUST run a secret scan (gitleaks) and a redaction step over all captured
  output.
- Agents MUST NOT print, copy, or echo secret values into any artifact or conversation.

### VIII. Safe Action Boundary (NON-NEGOTIABLE)

- The LLM MUST only PROPOSE a structured action. Model output is untrusted input.
- The application MUST validate every proposal against the schema, invariants, and
  guardrails before applying anything.
- Prompt-injection text in a user request MUST NOT cause a destructive or unauthorised
  action.
- The application MUST NOT invent entity IDs; every ID it uses MUST come from existing
  repository state.
- No request MAY trigger a bulk destructive action.
- The SDK's built-in tools (shell, file read/write, web) MUST be unavailable to the model.
  A test MUST assert that sessions are created with no tools and a deny-all permission
  handler.

### IX. Engineering Quality

- SOLID MUST be followed strictly, with one-way layering `api -> services -> llm adapter ->
  models`. A lower layer MUST NOT import a higher layer.
- Routers (`api`) MUST contain only request/response handling: no business logic and no
  LLM calls. Services MUST NOT build HTTP responses. The repository MUST contain no business
  rules.
- Services MUST depend on abstractions (`typing.Protocol`) and receive them through FastAPI
  `Depends`, never by instantiating concrete classes inline. The LLM client MUST sit behind
  the `LLMClient` Protocol so it can be stubbed or replayed.
- Each module MUST have a single reason to change; implementations MUST be substitutable for
  their abstractions; interfaces MUST be small and role-specific.
- All functions, methods, and class attributes MUST be fully annotated. `mypy --strict` MUST
  report zero errors. `Any` and `# type: ignore` MUST NOT be used without a one-line
  justification on the same line.
- Ruff MUST report zero errors. Bandit MUST report no medium or high findings.
- Pydantic v2 validation MUST be applied to every request body, query parameter, path
  parameter, and model output, with `extra="forbid"`. Invalid input MUST return HTTP 422
  (schema) or 400 (business rule) and MUST NOT reach the service layer.
- Typed domain exceptions MUST be raised from services and mapped in one central handler that
  returns the uniform error body `{"error": {"code": "...", "message": "..."}}`. Unexpected
  errors MUST return a generic HTTP 500 in the same shape. Stack traces, paths, and internals
  MUST NOT leak in any response.
- Bare `except` and swallowed exceptions MUST NOT be used.
- Functions MUST NOT exceed the function length or complexity limits in the Measurable
  Engineering Constraints table.
- The API MUST be versioned under `/api/v1`, documented by the generated OpenAPI schema, and
  every list endpoint MUST be paginated with a documented maximum page size.
- Dependencies MUST be pinned. If CORS is enabled, it MUST allow only configured origins.
- New dependencies, services, or abstractions MUST be justified in the plan's complexity
  section (YAGNI).

### X. Tests First (NON-NEGOTIABLE)

- Unit and contract tests MUST be written from the approved acceptance criteria and observed
  failing before the code that satisfies them is written (red -> green -> refactor).
- Every API endpoint MUST have at least one success and one failure contract test.
- Every bug fix MUST add a regression test or an eval case that fails before the fix.
- Coverage minimums are in the Measurable Engineering Constraints table and MUST NOT be
  lowered.

### XI. Evidence

The following layout is REQUIRED, relative to `assignment_2/`:

- `evidence/initial-generation/`: snapshot of the first agent output, git-tagged
  `assignment-2-initial-generation` BEFORE the first harness run. The snapshot is a directory
  or a `.tar.gz` archive of the tagged commit with a manifest and a checksum.
- `evidence/final-generation/`: snapshot of the accepted output, in the same form.
- `evidence/harness-results/<UTC-timestamp>/`: raw stdout/stderr/exit codes, junit and
  coverage reports, results JSON, and `summary.json` for each run.
- `evidence/eval-results.json`: produced by a live run only (Principle VI).
- `evidence/harness-log.md`: the run log.

`evidence/harness-log.md` MUST contain these sections in this order:

1. Human Approval.
2. Initial generation, with the task/spec context given to the agent.
3. Failure-and-repair log.
4. Quickstart validation.
5. Convergence results.
6. Acceptance traceability table (every FR, INV, GR, and AC mapped to at least one
   automated test or eval case).
7. Final human ACCEPT/REJECT decision, with known limitations and residual risks.
8. Run table, LAST.

Log rules:

- `run.sh` MUST append exactly one row to the END of the run table, which is the end of the
  file. It MUST NOT write to any other section.
- Harness output MUST be generated by the runner, never typed by hand.
- Every genuine, unexpected failure MUST be logged as specified in Principle XII (Failure
  logging). Failures MUST NOT be invented.
- Each live run MUST log: model id, `reasoning_effort`, SDK version, request count,
  threshold, and scoring formula. It MUST NOT log secrets.
- The agent MUST NOT write the final ACCEPT/REJECT decision; a human records it.

### XII. Agent Guardrails and Human Approval (NON-NEGOTIABLE)

- **Approval gate**: implementation MUST NOT start until a human has recorded `APPROVED`,
  their name, and the date for `spec.md`, `plan.md`, and `tasks.md` in the Approval section
  of `evidence/harness-log.md`. This is task T001; the agent MUST stop and wait for it.
- The coding agent MUST receive the approved specification context, this constitution, and
  the relevant tasks before generating code.
- **No running ahead**: the agent MUST implement one phase at a time, stop at each phase
  checkpoint to report completed tasks and gate results, and halt on the first failing
  non-parallel task. A task MUST be marked `[X]` only after its tests pass.
- **First generation preserved**: after the last implementation task and before the first
  `.harness/run.sh`, the code MUST be committed, tagged `assignment-2-initial-generation`, and copied to
  `evidence/initial-generation/`. The repaired version goes to `evidence/final-generation/`.
- **Self-healing**: failure evidence is fed to the coding agent, the implementation is
  repaired, and the same gates are rerun unchanged. Repair attempts are counted per failure
  and MUST NOT exceed the limit in the Measurable Engineering Constraints table.
- **Failure logging**: every genuine, unexpected failure MUST be entered in the
  failure-and-repair log of `evidence/harness-log.md` when it occurs, whether it appears in a
  task's test run, at a phase checkpoint, in a gate script run, or in a recorded run. A
  failure is unexpected when a test or gate that should pass does not. Tests written first
  that fail as intended (Principle X) are not repair events; their failure summary belongs in
  the commit message. Each entry MUST state: the failing case ID or gate/test, the failed
  requirement or property, expected vs observed behaviour, the evidence fed back to the agent,
  the change made (commit and files), and the re-run outcome of the same checks unchanged.
  The entry MUST be written no later than the commit that contains the fix. A phase with no
  unexpected failure MUST be logged as "no repair needed".

## Technology & Environment

- Python 3.12 selected with `pyenv`, pinned in `.python-version` containing `3.12`.
- A single `.venv` created with `python3.12 -m venv .venv` inside `assignment_2/`. Every
  Python dependency install MUST target this `.venv` and MUST NOT be installed globally.
- `uv` is the only Python dependency tool. Dependencies MUST be declared in
  `src/backend/pyproject.toml`, locked in `src/backend/uv.lock` (committed), and installed
  with `uv sync --active` (or `uv pip install` with `VIRTUAL_ENV` set to the `.venv`).
  `requirements.txt` MUST NOT exist.
- The application MUST be a small FastAPI HTTP API with an in-memory repository only. It
  MUST NOT include browser or Playwright tests.
- Repository layout, relative to `assignment_2/`: `src/backend`, `tests/backend`,
  `evals/`, `.harness/`, `evidence/`, `specs/`, `.specify/`. `.venv/`, build outputs, and
  caches MUST be excluded through `.gitignore`.
- LLM access MUST be ONLY through the Copilot SDK for Python (`github-copilot-sdk`), pinned
  to an exact version in `uv.lock`. LangChain and other LLM frameworks MUST NOT be used
  unless the plan justifies them in writing.
- All SDK usage MUST live in one module behind the `LLMClient` Protocol. No other module
  MAY import `copilot`.
- The SDK runtime MUST be configured least-privilege:
  - `CopilotClient(mode="empty")`;
  - `available_tools=[]` and no state-mutating custom tools;
  - a permission handler that REJECTS every request (`PermissionHandler.approve_all` MUST
    NOT be used);
  - memory disabled and infinite sessions disabled;
  - one fresh session per request;
  - an empty temporary working directory.
- The model MUST return structured output via a response schema (a Pydantic model with
  `extra="forbid"`). The application, not the model, applies actions.
- Auth MUST use the logged-in Copilot user, or `GH_TOKEN` / `COPILOT_GITHUB_TOKEN` from
  `.env`.
- The SDK exposes no temperature. Determinism MUST be controlled by a fixed model id, low
  `reasoning_effort`, the response schema, and a repeat-run consistency check (K per the
  Measurable Engineering Constraints table).
- Before coding against the SDK, the agent MUST verify the installed package's actual
  signatures; documentation examples differ between versions.
- A `README.md` in `assignment_2/` MUST document setup (pyenv, venv, uv), how to start the
  API, and how to run the harness, with copy-pasteable commands.

## Repository & Workflow Constraints (NON-NEGOTIABLE)

- All work MUST happen in the existing git repository AI-SDLC (remote origin:
  `github.com/smandalsid/AI-SDLC`), on the dedicated branch `assignment-2-reminder-agent`,
  never on `main`.
- Before any work, and before every commit, the agent MUST verify that the current branch
  is not `main`. If it is `main`, the agent MUST stop and ask.
- All work MUST live entirely inside `assignment_2/`. The agent MUST NOT create, modify, or
  delete anything outside `assignment_2/`; everything outside it is read-only.
- Every path in the spec, plan, tasks, harness, and evidence MUST be relative to
  `assignment_2/`. Spec Kit artifacts MUST live in `assignment_2/.specify/` and
  `assignment_2/specs/`.
- The agent MUST NOT push to any remote, force-push, merge into `main`, rebase published
  history, delete branches, or open pull requests. The human performs all pushes and merges
  after the final ACCEPT decision.
- Local commits are allowed on the feature branch only. Commits MUST be small, and
  milestones MUST be committed: approved artifacts, foundation with harness, each user
  story, the `assignment-2-initial-generation` tag, each repair, and the final generation.
- Commit messages MUST be conventional (`feat:`, `fix:`, `test:`, `docs:`, `chore:`) and MUST
  reference the task IDs.
- Staging MUST be explicit, using named paths inside `assignment_2/`. `git add -A` and
  `git add .` MUST NOT be used. `.env`, `.venv/`, caches, secrets, and hand-edited harness
  output MUST NOT be staged. The secret scan (gitleaks) MUST also run against the staged
  diff.
- The harness MUST fail the run if `git diff --name-only main...HEAD` lists any path outside
  `assignment_2/`.

## Measurable Engineering Constraints

Each constraint is binary and is verified by the harness or a named tool. Numeric values are
stored in `.harness/config/thresholds.env`. A breach MUST fail the run, except MEC-17, where
the run is INVALID.

| ID     | Constraint                                                                  | Limit                                         | Verified by          |
|--------|-----------------------------------------------------------------------------|-----------------------------------------------|----------------------|
| MEC-1  | Eval cases in `evals/dataset.json`                                          | >= 15                                         | Eval gate            |
| MEC-2  | Cases per category (normal, boundary, ambiguous, missing-info, malformed, adversarial/guardrail) | >= 2 each                | Eval gate            |
| MEC-3  | Requirement traceability of eval cases                                      | 100%                                          | Eval gate            |
| MEC-4  | Schema validity (non-`INFRA_ERROR` cases)                                   | 100%                                          | Eval gate (Layer 1)  |
| MEC-5  | Guardrail/invariant cases passing                                           | 100%                                          | Eval gate (Layer 2)  |
| MEC-6  | Aggregate score                                                             | >= threshold declared in the spec (hard gate) | Eval gate (Layer 3)  |
| MEC-7  | Backend line coverage                                                       | >= 85%                                        | Test gate            |
| MEC-8  | Backend branch coverage                                                     | >= 80%                                        | Test gate            |
| MEC-9  | Function length                                                             | <= 40 lines                                   | Lint gate            |
| MEC-10 | Cyclomatic complexity per function (Ruff `C901`)                            | <= 10                                         | Lint gate            |
| MEC-11 | `ruff check` and `ruff format --check` findings                             | 0                                             | Lint gate            |
| MEC-12 | `mypy --strict` errors                                                      | 0                                             | Lint gate            |
| MEC-13 | `bandit -ll` medium/high findings                                           | 0                                             | Security gate        |
| MEC-14 | `pip-audit` findings                                                        | 0                                             | Security gate        |
| MEC-15 | `gitleaks` findings in tracked files, staged diff, and evidence             | 0                                             | Security gate        |
| MEC-16 | Repair attempts per failure                                                 | <= 5                                          | Process / log review |
| MEC-17 | `INFRA_ERROR` share of cases                                                | <= 10%, otherwise run is INVALID              | Eval gate            |
| MEC-18 | Live eval requests per full run                                             | <= 60                                         | Eval gate            |
| MEC-19 | Repeat runs per case for consistency (FR-9)                                 | 3                                             | Eval gate            |
| MEC-20 | Endpoints with >= 1 success and >= 1 failure contract test                  | 100%                                          | Test gate            |
| MEC-21 | Skipped or xfail tests without a documented reason                          | 0                                             | Test gate            |
| MEC-22 | Pagination: default page size 20, maximum 100; larger values return 422     | Exact                                         | Contract tests       |
| MEC-23 | Harness scripts, thresholds, dataset, schema, and tool config match `checksums.sha256` | 100% match                         | Integrity gate       |
| MEC-24 | Traceability: every FR, INV, GR, and AC maps to >= 1 automated test or eval case | 100%                                     | Review of log table  |
| MEC-25 | Unexpected failures logged with evidence, fix, and re-run outcome           | 100%                                          | Review of log        |
| MEC-26 | Reproducibility: fresh clone + `.env` + one documented command runs API and harness | Succeeds                              | Documented check     |
| MEC-27 | Files changed outside `assignment_2/` relative to `main`                    | 0                                             | Scope gate           |

## Deterministic Harness & Evidence

`.harness/run.sh` is the single entry point. It MUST execute all gates in order, continue
after a failure to collect all evidence, and exit non-zero if any gate failed:

0. **Integrity Guard**: checksums of the harness, thresholds, dataset, schema, and tool
   configuration; plus the scope check (MEC-27).
1. **Syntax & Lint Guard**: Ruff, mypy.
2. **Security / SAST Guard**: Bandit, pip-audit, gitleaks, and the redaction step.
3. **Unit & Contract Tests**: pytest with coverage; all mandatory tests MUST pass and
   coverage thresholds MUST be met.
4. **Evaluation**: Layers 1-3 (Principle IV) in `--mode live` or `--mode replay`.
5. **Feedback Capture**: for each failure, record stdout/stderr, the failed rule or test, the
   expected behaviour, and the observed behaviour (secrets redacted) in `summary.json`.
6. **Self-Healing**: feed the captured evidence to the coding agent, repair, and rerun the
   same gates unchanged (Principle XII).
7. **Human Review**: a human records the final ACCEPT or REJECT decision after the live run.

- Individual gate scripts MAY be run while developing. Only runs made through
  `.harness/run.sh` count as evidence, and the first such run happens only after the
  `assignment-2-initial-generation` snapshot.
- A partial PASS MUST be treated as a REJECT.

Required layout, relative to `assignment_2/`:

```text
.specify/ and specs/        Spec Kit artifacts (constitution, spec, plan, tasks)
src/backend/                application code, pyproject.toml, uv.lock
tests/backend/              unit and contract tests
evals/                      dataset.json and output schema
.harness/                   gate scripts, run.sh, summarizer
  config/thresholds.env     all numeric thresholds
  config/checksums.sha256   integrity checksums
evidence/                   see Principle XI
```

## Development Workflow & Quality Gates

- Workflow order: constitution -> specify -> clarify -> plan -> tasks -> analyze -> human
  approval -> implement (phase by phase) -> snapshot of the first generation -> harness ->
  repair -> converge -> human decision.
- A human MUST approve the spec, plan, and tasks before `/speckit-implement` (Principle XII).
- Run `/speckit-analyze` before implementation and `/speckit-converge` after it.
- Tests derived from acceptance criteria MUST exist and fail before the corresponding
  implementation is written.
- After each task, its tests MUST be run. An unexpected failure MUST be logged in the
  failure-and-repair log before the task is marked `[X]`.
- A change is accepted only when every gate passes on the final code and a human records
  ACCEPT.
- Code comments MUST explain intent the code cannot show; they MUST NOT restate the code.

## Governance

- This constitution supersedes all other practices for this project. Principles I, III, V,
  VII, VIII, X, XII and the Repository & Workflow Constraints are NON-NEGOTIABLE and MUST NOT
  be waived by any spec, plan, task, or agent instruction.
- Amendments MUST be made by editing this file, stating the reason, the version bump, and any
  impact on existing artifacts. Dependent specs, plans, and tasks MUST be re-checked after an
  amendment. Amendments are semver-versioned and recorded in a Sync Impact Report:
  - MAJOR: backward-incompatible removal or redefinition of a principle or constraint;
  - MINOR: a new principle or section, or materially expanded guidance;
  - PATCH: clarification, wording, or typo fixes.
- An amendment MUST NOT lower or relax a limit in the Measurable Engineering Constraints
  table, or any NON-NEGOTIABLE rule, merely to make a failing run pass. Any such change MUST
  be a human decision recorded in `evidence/harness-log.md`.
- Compliance MUST be reviewed at plan time (a Constitution Check in `plan.md`), at
  `/speckit-analyze` time, and at the human ACCEPT/REJECT decision, each against every
  principle and every table row. A violation MUST be fixed or explicitly justified in the
  plan's complexity-tracking table before the next phase starts.

**Version**: 1.0.2 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-06
