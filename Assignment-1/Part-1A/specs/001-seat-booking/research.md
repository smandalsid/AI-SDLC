# Research: Bus Seat Booking

All technical unknowns are resolved. Format: Decision, Rationale, Alternatives considered.

## 1. Database engine and image

- **Decision**: `mcr.microsoft.com/azure-sql-edge`, container `azure-sql-edge`, already running on port 1433
  (verified: TCP reachable inside the container, `ACCEPT_EULA=1`, SA password supplied through the container
  environment). Colima runs natively on arm64 (verified: `aarch64`, Virtualization.Framework).
- **Rationale**: User-mandated; native arm64 so no Rosetta; speaks T-SQL/TDS like Azure SQL.
- **Risks**: Microsoft has retired Azure SQL Edge (end of support 30 Sept 2025); the image remains pullable but
  receives no updates. Mitigation: only portable T-SQL; swap to `mcr.microsoft.com/mssql/server` is a compose
  change (amd64 on Apple Silicon would then need Rosetta).
- **Alternatives**: `mssql/server` (needs emulation on arm64); SQLite (violates the stated database).
- **Fact found**: the image contains no `sqlcmd`/`mssql-tools`, so schema and data are applied from Python, and
  the healthcheck uses a TCP probe (`bash -c 'echo > /dev/tcp/127.0.0.1/1433'`, verified working).

## 2. Python database driver

- **Decision**: `pymssql` with SQLAlchemy URL `mssql+pymssql://`.
- **Rationale**: A binary wheel exists for this machine (`pymssql-2.4.6-cp312-cp312-macosx_15_0_arm64`, verified by
  download) and it bundles FreeTDS, so no ODBC driver or Homebrew tap is needed.
- **Alternatives**: `pyodbc` + Microsoft ODBC Driver 18 (needs `brew` tap, `unixodbc`, and a source rebuild on
  macOS, prone to proxy and linking issues); `aioodbc`/async drivers (extra complexity, not needed at this scale).
- **Fallback**: switch URL to `mssql+pyodbc://` if pymssql misbehaves; only `db/session.py` changes.

## 3. Sync vs async backend

- **Decision**: Synchronous SQLAlchemy 2.0 and plain `def` endpoints.
- **Rationale**: Simplest correct model; FastAPI runs sync endpoints in a thread pool; pymssql is blocking.
- **Alternatives**: async SQLAlchemy (no mature async pymssql path).

## 4. Preventing double-booking

- **Decision**: `UNIQUE (bus_id, seat_number)` on `bookings`. Insert all requested seats in one transaction;
  on `IntegrityError` roll back and raise `SeatAlreadyBookedError`.
- **Rationale**: Race-free without explicit locks; also satisfies the all-or-nothing rule (FR-014) and the
  constitution's "database constraint in addition to service checks".
- **Alternatives**: `SELECT ... WITH (UPDLOCK)` then insert (more code, lock contention, still needs the
  constraint); optimistic version column (unneeded).

## 5. Schema management and test database

- **Decision**: Alembic migration `0001`; seed script separate and idempotent; test database
  `bus_db_test` created and migrated by the pytest session fixture; reset between tests via the seed routine.
- **Rationale**: Constitution VIII; the test schema is the real migrated schema; concurrency tests need real
  commits so transactional rollback isolation is unsuitable.
- **Alternatives**: `Base.metadata.create_all` (skips migrations, can drift); SQLite for tests (different SQL
  semantics, cannot prove the unique-index behaviour on SQL Server).

## 6. Seats as derived values

- **Decision**: No `seats` table; seats are `1..buses.total_seats`; status derived from `bookings`.
- **Rationale**: Constitution VIII, spec FR-002; one query for the bus and one for its booked seat numbers.
- **Alternatives**: a `seats` table (more rows, no extra capability in this feature).

## 7. Pagination and seat list size

- **Decision**: `page` (default 1) and `page_size` (default 20, max 100) on bus and user lists; the seat list is
  returned whole because `total_seats` has `CHECK (total_seats BETWEEN 1 AND 60)`.
- **Rationale**: Constitution IX; the seat list is bounded and must be shown in full.

## 8. Error shape

- **Decision**: Replace FastAPI's default validation error body with the constitution's
  `{"error": {"code", "message"}}`; one handler module; 503 on database operational errors.
- **Rationale**: Constitution IV; the frontend needs stable codes to choose among its three messages.

## 9. Frontend stack

- **Decision**: React + Vite + TypeScript; `react-router-dom` for two lazy routes; native `fetch`; custom hooks;
  plain CSS (mobile-first, CSS grid).
- **Rationale**: Meets the 200 KB budget and constitution X; no state or fetching library is needed for two
  screens.
- **Alternatives**: React Query (extra weight), UI kits (heavy), a single page without a router (violates
  code-split routes).

## 10. Frontend testing and browser checks

- **Decision**: Vitest + React Testing Library with `vi.mock` on the API client modules (no extra mocking
  library). Playwright for reload persistence and responsive overflow only.
- **Rationale**: jsdom has no layout engine, so overflow at 320/768/1280 px and real reload behaviour need a
  browser. Verified: the Playwright Chromium download is blocked by the corporate proxy, so the installed
  Microsoft Edge is used (`channel: "msedge"`); `gitleaks` installs through Homebrew.

## 11. Secret scan and function-length gates

- **Decision**: `gitleaks` for secrets (installed via Homebrew; if blocked, download in a browser as in prior
  proxy issues); a 30-line AST script for the 40-line function limit, since Ruff has no such rule.

## 11a. Harness design (lessons from the first attempt)

- **Decision**: build `.harness/` first (gates, `thresholds.env`, integrity checksums, summariser, runner) in
  the Foundational phase; require a human approval gate (T001); implement phase by phase with checkpoints;
  snapshot and tag the first generation before the first recorded run; bound repairs to 5 attempts per gate.
- **Rationale**: in the first attempt the harness tasks sat in the last phase, so the run stopped before they
  were reached and no evidence existed; nothing stopped the agent from running ahead. A reference harness
  (calculator project) shows the working pattern: thresholds in one config file, an integrity gate over the
  scripts, a summariser that records expected-versus-observed per failed test, and a runner that appends to
  `harness-log.md`.
- **Alternatives**: harness last (rejected, failed); only ad hoc tool runs (rejected, no evidence).
- **Python tooling**: pyenv 3.12, root `.venv`, `uv` with `pyproject.toml` and `uv.lock` (constitution v1.3.0)
  replaces pinned requirements files.

## 12. Identity and time

- **Decision**: Integer identity keys; `booked_at` is `DATETIME2` in UTC supplied by an injected `Clock`.
- **Rationale**: Simple, indexable, deterministic in tests (fake clock); spec FR-012.

## 13. Application database account

- **Decision**: Use `DB_USER` from `.env` (currently `sa`) for this local mock-data environment; documented in
  Complexity Tracking; swapping to a least-privilege login needs no code change.
