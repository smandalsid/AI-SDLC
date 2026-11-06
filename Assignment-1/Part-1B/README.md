# Natural-Language Reminder Agent

A small API that turns one free-form reminder request into exactly one validated action
(`create`, `reschedule`, `snooze`, `cancel`, `clarify`, or `refuse`) and applies it to an in-memory
copy of the reminders you send. The language model only proposes an action; the application validates
it before anything is applied.

Specification, plan, tasks and contracts live in `specs/001-nl-reminder-agent/`. The project rules are
in `.specify/memory/constitution.md`.

## Setup

Run from `Assignment-1/Part-1B/` (formerly `assignment_2/`).

```bash
pyenv local 3.12
python3.12 -m venv .venv && source .venv/bin/activate
cd src/backend && uv sync --active && cd ../..
python -m copilot download-runtime       # one-time download of the SDK runtime
cp .env.example .env                     # then edit; .env is gitignored
```

Authentication is the logged-in GitHub user (`gh auth status`). For unattended runs set `GH_TOKEN` or
`COPILOT_GITHUB_TOKEN` in `.env` only; never paste a token into a command, file, or chat.

## Run the API

```bash
uvicorn app.api.main:create_app --factory --app-dir src/backend --port 8000
```

```bash
curl -s localhost:8000/api/v1/actions -H 'content-type: application/json' -d '{
  "text": "remind me to pay rent next Monday at 9am",
  "timezone": "Asia/Kolkata",
  "now": "2026-11-05T10:00:00+05:30"
}'
```

`GET /api/v1/health` answers without calling the model. The full contract is
`specs/001-nl-reminder-agent/contracts/openapi.yaml`.

## Gates and the evaluation harness

One command runs every gate in order (integrity, lint and types, security, tests with coverage,
evaluation) and appends a row to the end of `evidence/harness-log.md`:

```bash
.harness/run.sh --mode replay    # recorded responses; fast, never final
.harness/run.sh --mode live      # real model; the only mode that can support an ACCEPT decision
```

The gates can also be run one at a time while developing:

```bash
bash .harness/integrity.sh
bash .harness/lint.sh
bash .harness/security.sh
bash .harness/test.sh
```

Thresholds live only in `.harness/config/thresholds.env`; the files that protect the harness are listed in
`.harness/config/checksums.sha256`, which a human regenerates after an approved change.

## Evidence layout

| Path | Content |
|------|---------|
| `evidence/harness-log.md` | approval, failure-and-repair log, traceability table, human decision, run table (last) |
| `evidence/initial-generation/` | snapshot of the first generated implementation, taken before the first run |
| `evidence/harness-results/<UTC-timestamp>/` | per-gate output, `summary.json`, and (live runs) `eval-results.json` |
| `evidence/final-generation/` | snapshot of the final implementation |

## Corporate proxy fallbacks

If `python -m copilot download-runtime` fails (for example an HTML single sign-on page is returned instead
of the archive, or a TLS error), try in order and never disable TLS verification:

1. Export the corporate root and issuing CAs from the macOS keychain into a PEM bundle and set
   `SSL_CERT_FILE` for the download only.
2. Download the platform archive in a signed-in browser, extract it, and set `COPILOT_CLI_PATH` to the
   runtime plus `COPILOT_SKIP_CLI_DOWNLOAD=1`.
3. Mirror the release assets and set `COPILOT_CLI_DOWNLOAD_BASE_URL`.
