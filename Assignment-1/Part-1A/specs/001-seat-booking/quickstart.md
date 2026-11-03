# Quickstart: Bus Seat Booking

Validation guide for the feature once implemented. Contracts: [contracts/openapi.yaml](contracts/openapi.yaml).
Data details: [data-model.md](data-model.md).

## Prerequisites

- Colima installed. `scripts/dev.sh` starts Colima and the `azure-sql-edge` container (port 1433) when they are not
  running; an already-running container is reused untouched.
- Python 3.12, Node 24 (or any current LTS), npm.
- `.env` at the repository root with `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Optional: `DB_HOST` (default
  `localhost`), `DB_PORT` (default `1433`), `CORS_ORIGINS` (default `http://localhost:5173`). Never commit it.

## One-time setup

```bash
pyenv local 3.12 && python3.12 -m venv .venv && source .venv/bin/activate
(cd src/backend && uv sync --active)
npm --prefix src/frontend ci
```

Playwright uses the manually installed Google Chrome Canary (`channel: "chrome-canary"`): the Chromium download is
blocked by the corporate proxy and Edge forbids remote debugging by managed policy. `gitleaks` is needed for the
security gate (`brew install gitleaks`).

## Create the development database and mock data

```bash
scripts/db-init.sh
```

Expected: waits for the database, creates `bus_db` if missing, applies migration `0001`, seeds 3 buses
(ids 1-3), 3 users (ids 1-3), 0 bookings. Running it again prints the same end state.

## Run the application

Single command (starts or reuses the DB container, initialises `bus_db`, starts backend and frontend):

```bash
scripts/dev.sh
```

Or manually:

```bash
# terminal 1 (backend, port 8000)
cd src/backend && uvicorn app.main:create_app --factory --reload
# terminal 2 (frontend, port 5173; proxies /api to the backend)
npm --prefix src/frontend run dev
```

## Validation scenarios

1. **List buses**: `curl -s localhost:8000/api/v1/buses` returns 3 buses; Bus A has `total_seats` 20.
2. **View seats**: `curl -s localhost:8000/api/v1/buses/1` returns 20 seats, all `available`.
3. **Book**:
   `curl -s -X POST localhost:8000/api/v1/bookings -H 'content-type: application/json' -d '{"bus_id":1,"user_id":1,"seat_numbers":[3,4]}'`
   returns 201 with two bookings sharing one `booked_at`.
4. **Reflected**: repeat step 2; seats 3 and 4 are `booked`. Repeat step 3; expect 409 `seat_unavailable`.
5. **Validation**: empty list, duplicate seats, 7 seats, and seat 0 return 422; seat 21 on Bus A returns 400;
   bus 99 or user 99 returns 404. Each body is `{"error": {"code", "message"}}`.
6. **UI**: open http://localhost:5173, choose Bus A, choose "Asha", select seats 5 and 6, Confirm. A success
   message lists seats 5 and 6 and they become booked; reload the page and they remain booked.
7. **Conflict in UI**: book seat 7 via `curl`, then in a stale UI tab select seat 7 and Confirm; the UI shows
   "seat no longer available" and refreshes.
8. **Reset**: `scripts/db-init.sh` returns the database to the seeded state.

## Test database and automated checks

```bash
scripts/db-test-init.sh            # optional; pytest also does this automatically
(cd src/backend && pytest)         # unit, contract, integration (creates bus_db_test)
(cd src/backend && pytest -m perf) # latency checks with 1,000 bookings
npm --prefix src/frontend test     # Vitest + RTL
npm --prefix src/frontend run e2e  # Playwright (starts backend on bus_db_test via scripts/e2e-backend.sh)
.harness/run.sh                    # all gates; exit code 0 only if every gate passes
```

Expected: the harness writes `evidence/harness-results/<timestamp>/summary.json` with PASS/FAIL per gate and
appends a row to the run table in `evidence/harness-log.md`; coverage at or above 85% (backend line), 80%
(backend branch), and 80% (frontend line). Use `.harness/run.sh --dry-run` to try the harness without recording
evidence.

## Evidence workflow

1. A human records `APPROVED` for spec, plan, and tasks in `evidence/harness-log.md` (task T001).
2. Implement phase by phase (harness first); at each checkpoint run the individual gate scripts and commit.
3. After the last implementation task: commit, tag `initial-generation`, and copy `src/`, `tests/`, `.harness/`
   and the approved artifacts to `evidence/initial-generation/`.
4. Run `.harness/run.sh`; on failure, give the results folder to the coding agent, repair, re-run the same gates
   unchanged (at most 5 attempts per gate), and log each step in `evidence/harness-log.md`.
5. Run `/speckit-converge`, copy the final code to `evidence/final-generation/`, and have a human record the
   ACCEPT/REJECT decision.
