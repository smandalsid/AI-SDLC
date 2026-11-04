# Bus Seat Booking

Web application for viewing buses and booking seats (feature `001-seat-booking`) behind a username and password sign-in (feature `002-user-authentication`). FastAPI + SQLAlchemy + Azure SQL Edge on the backend, React + Vite on the frontend. The specifications live in [specs/001-seat-booking/](specs/001-seat-booking/) and [specs/002-user-authentication/](specs/002-user-authentication/); the governing rules are in `.specify/memory/constitution.md`.

## Prerequisites

- pyenv with Python 3.12 (`pyenv local 3.12` writes `.python-version`)
- A virtual environment at the repository root: `python3.12 -m venv .venv && source .venv/bin/activate`
- [uv](https://docs.astral.sh/uv/) for backend dependencies
- Node (current LTS) and npm
- Colima and the Docker CLI (see below)
- Google Chrome Canary for the Playwright end-to-end tests (Chromium downloads and Edge remote debugging are blocked on the managed machine; `playwright.config.ts` uses `channel: "chrome-canary"`)
- `gitleaks` for the security gate (`brew install gitleaks`)

## Setup

```bash
source .venv/bin/activate
(cd src/backend && uv sync --active)
npm --prefix src/frontend ci
```

## Configuration

Copy `.env.example` to `.env` (never commit it) and fill in the values. Variable names:

| Name | Required | Default |
|------|----------|---------|
| `DB_NAME` | yes | |
| `DB_USER` | yes | |
| `DB_PASSWORD` | yes | |
| `DB_HOST` | no | `localhost` |
| `DB_PORT` | no | `1433` |
| `CORS_ORIGINS` | no | `http://localhost:5173` |
| `JWT_SECRET` | yes | |
| `MOCK_USER_PASSWORDS` | yes for the seed | |

`JWT_SECRET` signs the sign-in tokens; the application refuses to start without it. Create a value in your own terminal and paste it into `.env` (the value is never printed by the project or committed):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

`MOCK_USER_PASSWORDS` is one JSON object with a password you choose for each mock user, for example `{"asha":"...","ravi":"...","meera":"..."}` (see `.env.example` for the shape). Only the seed command reads it; the passwords are stored as Argon2id hashes and are never written to the source, the logs, or the database in plain text.

Settings are read only through `src/backend/app/core/config.py`.

## Database container and Colima

The database runs as the container `azure-sql-edge` (`mcr.microsoft.com/azure-sql-edge`, port 1433), defined in `docker-compose.yml`. Azure SQL Edge is retired but its image can still be pulled; the SQL used is portable T-SQL, so the swap path is to point `docker-compose.yml` at `mcr.microsoft.com/mssql/server` (needs an amd64 image or emulation on Apple silicon) without application changes.

On this machine Docker runs through Colima. The `docker compose` plugin is not installed, so `scripts/dev.sh` falls back to `docker run` with the same image, port, volume, and health check when it has to create the container.

**The existing container is used as is.** The hand-started `azure-sql-edge` container is kept; it was not replaced by a compose-managed one (decision recorded under T125). It may hold other databases (for example `mid_dev`) that this project never touches. `scripts/dev.sh`:

1. starts Colima if the Docker daemon is not reachable;
2. reuses a running container untouched, waiting up to 60 s for its port if needed;
3. starts a stopped container with `docker start`;
4. refuses to start a second instance if another process already holds the port;
5. creates the container only when it does not exist and the port is free.

It never stops, removes, or recreates a container.

## Run

```bash
scripts/dev.sh
```

This makes the database available, creates and migrates `DB_NAME`, loads the mock data (3 buses, 3 users, no bookings), then starts the API on http://127.0.0.1:8000 and the frontend on http://localhost:5173. Ctrl-C stops only the processes it started; the database container keeps running.

`scripts/dev.sh --check` prints which database branch would be taken without acting; `scripts/dev.sh --db-only` makes the database available and exits. `scripts/db-init.sh` resets the development database to the mock data.

## Signing in

The mock users are `asha`, `ravi`, and `meera`; their passwords are the ones you put in `MOCK_USER_PASSWORDS`. Open http://localhost:5173, which shows the sign-in screen, and enter the username and password. Everything else (buses, seats, bookings) needs a signed-in session, and a booking is stored under the signed-in user.

- **Sign out** with the button in the header. The session ends on the server at once and the old token stops working.
- **Sessions last 30 minutes** from sign-in and are not extended by use. After that the app returns to the sign-in screen with a message.
- **Throttling**: after 5 failed sign-ins for a username within 5 minutes, that username is refused for 60 seconds after its last failure, even with the right password (other usernames are unaffected).
- **Per tab**: the token is kept in `sessionStorage`, so each browser tab signs in on its own and closing the tab signs out.
- `scripts/db-init.sh` (also run by `scripts/dev.sh`) now applies the migrations and then hashes and loads the mock users from `MOCK_USER_PASSWORDS`; it resets the sessions and the sign-in history.

Known limits (see `specs/002-user-authentication/research.md`, section 16): tokens travel over plain HTTP in local development (a real deployment must use TLS), there is no Content-Security-Policy header, and no job deletes old sessions or sign-in rows.

## Tests and the harness

Commands from [specs/001-seat-booking/quickstart.md](specs/001-seat-booking/quickstart.md):

```bash
source .venv/bin/activate
(cd src/backend && pytest)           # unit, contract, integration (uses DB_NAME_test)
(cd src/backend && pytest -m perf)   # latency checks with 1,000 stored bookings
npm --prefix src/frontend test       # Vitest and Testing Library
npm --prefix src/frontend run e2e    # Playwright; starts the backend on DB_NAME_test
```

The deterministic harness runs six gates in order: integrity, lint, security, test, build, e2e.

```bash
.harness/run.sh            # recorded run: evidence/harness-results/<timestamp>/ and a row in evidence/harness-log.md
.harness/run.sh --dry-run  # same gates, nothing recorded
```

Thresholds are in `.harness/config/thresholds.env`; the scripts, thresholds, and lint/type configuration are checksummed (`.harness/integrity.sh`) and must not be loosened to obtain a pass. Only recorded runs after the first-generation snapshot (tag `<NNN>-initial-generation`, for feature 002 `002-initial-generation`) count as evidence.
