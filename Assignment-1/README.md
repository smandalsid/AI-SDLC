# Assignment 1: Spec-Driven Development and Harness Engineering

Two applications built with GitHub Spec Kit (constitution, specify, clarify, plan, tasks, analyze, implement) and checked by a harness that the coding agent cannot loosen: scripted gates, checksummed thresholds, and recorded evidence.

| Part | Application | Kind | Harness result | Final human decision |
|------|-------------|------|----------------|----------------------|
| [Part-1A](Part-1A/) | Bus seat booking, with sign-in | Deterministic | Six gates pass (integrity, lint, security, test, build, e2e) | ACCEPT (2026-11-04) |
| [Part-1B](Part-1B/) | Natural-language reminder agent | Non-deterministic (LLM) | Live evaluation PASS, aggregate 1.0 against a 0.85 threshold | ACCEPT (2026-11-06) |

## Part-1A: bus seat booking (deterministic)

- **What was built**: FastAPI, SQLAlchemy and Azure SQL Edge on the backend; React and Vite on the frontend. Feature `001-seat-booking` lets a user view buses and book seats. Feature `002-user-authentication` adds username and password sign-in, server-side sessions that expire after 30 minutes, sign-out, and throttling of repeated failed sign-ins.
- **Specification trail**: `specs/001-seat-booking/` and `specs/002-user-authentication/` (spec, clarifications, research, plan, data model, contracts, quickstart, checklists, tasks), under the rules in `.specify/memory/constitution.md`.
- **Harness** (`.harness/`): six ordered gates. A checksum gate protects the scripts, thresholds and lint/type configuration. `run.sh` records each run under `evidence/harness-results/<timestamp>/` and appends a row to `evidence/harness-log.md`.
- **Tests**: 702 backend tests pass, plus Vitest component tests and Playwright end-to-end tests.
- **Evidence**: `evidence/001-seat-booking/` holds the feature 001 cycle. `evidence/` itself holds feature 002 (initial-generation, final-generation, harness-results, `harness-log.md`). The log records, per phase, the failures found, the evidence fed back to the agent, the repair and the re-run, followed by the convergence results, the acceptance traceability table and the human decision with its known limitations.
- **Git tags**: `initial-generation` (feature 001) and `002-initial-generation` (feature 002) mark the first generated implementation before the first harness run.

## Part-1B: natural-language reminder agent (non-deterministic)

- **What was built**: a FastAPI service that turns one free-form reminder request into exactly one validated action (`create`, `reschedule`, `snooze`, `cancel`, `clarify` or `refuse`). The model only proposes; the application validates before anything is applied. The model is reached through the GitHub Copilot SDK.
- **Specification trail**: `specs/001-nl-reminder-agent/`. The system prompt is `prompts/system.md`.
- **Evaluation pipeline** (`.harness/`): `evals/dataset.json` holds 33 cases (at least 15 required, every case traced to a requirement), run through structural (JSON schema), property and semantic evaluators. Consistency cases run three times. Thresholds are fixed in `.harness/config/thresholds.env`. The cases span six categories (normal, boundary, ambiguous, missing information, adversarial, malformed), and guardrail behaviour is scored separately.
- **Tests**: 651 tests with 98 percent line coverage, in addition to the evaluation.
- **Evidence**: `evidence/harness-log.md`, `evidence/eval-results.json`, `evidence/harness-results/` (three live runs), and the `initial-generation` and `final-generation` snapshots with manifests and checksums.
- **Failure and repair**: the second live run failed (aggregate 0.9788; case N05 differed across its three runs, B05 and M04 failed). Regression tests were written first, the prompt rules were repaired, and the third run passed with 1.0.
- **Git tag**: `assignment-2-initial-generation`.

## Running each part

Each part is self-contained and runs from its own folder. Setup, configuration and run instructions are in [Part-1A/README.md](Part-1A/README.md) and [Part-1B/README.md](Part-1B/README.md). Both use pyenv with Python 3.12, a `.venv` inside the part, and uv. Secrets live only in each part's untracked `.env`; `.env.example` shows the variable names.

## Folder layout

```
Assignment-1/
├── README.md
├── Part-1A/   .specify  specs  src  tests  .harness  evidence
└── Part-1B/   .specify  specs  src  prompts  tests  evals  .harness  evidence
```

## Folder restructure note

Originally the parts were `assignment_1/` and `assignment_2/`. They were restructured into `Assignment-1/Part-1A/` and `Assignment-1/Part-1B/`. Recorded harness outputs, snapshots and the Part-1B log entries were produced under the old folder names and still show the old absolute paths and the phrase "outside `assignment_2/`". They are kept unchanged as the original record.
