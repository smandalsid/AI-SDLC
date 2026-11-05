# Research: Natural-Language Reminder Agent

**Branch**: `assignment-2-reminder-agent` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

All findings below were measured on this machine on 2026-11-05 with throwaway scripts in `/tmp/spike`
(outside the repository). 16 live model requests were used in total; they were a pre-harness spike and are
not part of any evaluation run. Everything marked "unverified" was not observed and MUST be covered by a
test with fakes before it is trusted.

## (a) Exact SDK API for the installed version

**Decision**: pin `github-copilot-sdk==1.0.28` (latest stable on PyPI; `1.0.29rc*` and `*.dev*` are
pre-releases and are not used). Python `>=3.11` is required; we use 3.12. Runtime dependencies pulled in:
`pydantic>=2.11`, `httpx>=0.24`, `python-dateutil`. The wheel is pure Python (`py3-none-any`); the native
runtime is downloaded separately (see (c)).

Signatures verified by introspection of the installed package (not from documentation):

| Item | Verified signature (1.0.28) |
|------|-----------------------------|
| Client | `CopilotClient(*, mode='copilot-cli', base_directory=None, connection=None, working_directory=None, log_level='info', env=None, github_token=None, use_logged_in_user=None, ...)` used as `async with` |
| Mode `"empty"` | requires `base_directory`, `session_fs`, or a `UriRuntimeConnection`; otherwise raises `ValueError` ("won't fall back to ~/.copilot") |
| Session | `await client.create_session(*, on_permission_request, model, reasoning_effort, available_tools, tools, system_message, infinite_sessions, memory, working_directory, enable_session_store, on_event, ...)`, used as `async with await ...` |
| Structured output | `await session.send_and_wait_typed(prompt, ResponseModel, *, timeout=60.0) -> ResponseModel` (experimental; needs pydantic >= 2.11). `send` / `send_and_wait` also accept `response_schema=` |
| Deny-all permissions | handler returns `copilot.rpc.PermissionDecisionReject(feedback=...)`; `PermissionHandler.approve_all` MUST NOT be used |
| Events | `on_event=callable` receives `SessionEvent`; the event `assistant.usage` carries `data.model` (the model that served the call), `input_tokens`, `output_tokens`, `cost` |
| Catalog | `client.rpc.models.get_built_in_catalog()`; `session.rpc.model.list()` gives price categories. `client.list_models()` returned `[]` in both client modes on this account, so it is NOT used |

**Least-privilege configuration confirmed to work** in one spike call: `mode="empty"`, a temporary
`base_directory`, a temporary `working_directory`, `available_tools=[]`, `infinite_sessions={"enabled": False}`,
`memory={"enabled": False}`, deny-all `on_permission_request`, `reasoning_effort="low"`, a fresh session per
request. A repository test MUST re-verify these keyword names against the installed SDK on every run
(`inspect.signature`), so that SDK drift fails the build instead of silently loosening the configuration.

**Prompt delivery**: `system_message={"mode": "replace", "content": <prompts/system.md + context>}` cut
input tokens from 1577 to 110 for a trivial request, and gives the application full control of the prompt.
The SDK documents `replace` as removing its own guardrails; this is acceptable here only because tools are
unavailable (`available_tools=[]`), every permission request is rejected, and Principle VIII treats model
output as untrusted anyway. This is recorded in the plan's Complexity Tracking.

**Response schema**: a *wire* model (`ProposedActionWire`: `extra="forbid"`, all 8 fields required, plain
types, `Literal` enums, nullable fields, no length/range constraints) is passed as the response type. The full
8-field schema was accepted by the runtime and a live call returned the expected AC-2 answer
(`2026-11-10T18:00:00+00:00`). Range and cross-field rules (INV-2/4/6/7, per-intent required fields) are
enforced by our own `ProposedAction` model after the call, not delegated to the provider, so they are
measurable by Layer 1.

**Alternatives considered**: `send_and_wait` + `response_schema=` dict (rejected: returns an event that still
needs parsing); `copilot-cli` mode (rejected: loads user configuration and tools by default, contrary to the
constitution).

## (b) Detecting and classifying SDK/runtime errors

Observed (live): 

| Trigger | Exception observed |
|---------|--------------------|
| Invalid/absent credential (`use_logged_in_user=False`, dummy token) | `copilot._jsonrpc.JsonRpcError`, `code=-32603`, "No GitHub OAuth token or Copilot HMAC key provided" |
| Timeout (`timeout=0.3`) | `builtins.TimeoutError`, "Timeout after 0.3s waiting for session.idle" |
| Missing runtime binary (`for_stdio(path=...)`) | `builtins.RuntimeError`, "Copilot CLI not found at ..." |
| Empty mode without `base_directory` | `builtins.ValueError` (our configuration bug, not infrastructure) |

Not observed (unverified; must be tested with fake exceptions and confirmed from the first live failure that
occurs): rate/usage-limit errors, mid-request process exit (`copilot._jsonrpc.ProcessExitedError`,
`copilot.client.StopError`), network errors during runtime download (`httpx.HTTPError`).

**Decision**: the adapter (`copilot_client.py`) is the only place that sees SDK exceptions. It maps them to
typed domain exceptions:

| Domain exception | Raised for | Harness class |
|------------------|-----------|---------------|
| `LLMInfrastructureError(kind="timeout")` | `TimeoutError` | `INFRA_ERROR` |
| `LLMInfrastructureError(kind="auth")` | `JsonRpcError` whose message matches the auth patterns (`OAuth token`, `HMAC`, `401`, `unauthor`, `forbidden`) | `INFRA_ERROR` |
| `LLMInfrastructureError(kind="rate_limit")` | `JsonRpcError` matching `rate limit`, `quota`, `usage limit`, `429` | `INFRA_ERROR` |
| `LLMInfrastructureError(kind="rpc")` | any other `JsonRpcError` | `INFRA_ERROR` |
| `LLMInfrastructureError(kind="runtime")` | `RuntimeError`, `FileNotFoundError`, `OSError`, `ConnectionError`, `ProcessExitedError`, `StopError`, `httpx.HTTPError` raised while starting or using the runtime | `INFRA_ERROR` |
| `LLMInfrastructureError(kind="model_routing")` | served model (`assistant.usage.data.model`) differs from the configured model id | `INFRA_ERROR` |
| `LLMOutputError` | the model answered but the JSON does not match the wire or domain schema (`pydantic.ValidationError`) | application result (not infra): case scored, API returns a controlled error (GR-5) |
| anything else | unexpected exception type | NOT infra: surfaces as HTTP 500 / case `ERROR`, counted as a failure, never hidden |

Matching is by exception type first, message pattern second; the unverified patterns are listed in one
constant table so the first real failure can be added without touching logic. `except Exception` is never
used: the adapter catches the explicit tuple above, which keeps the "no bare except" rule.

**Retry**: `INFRA_ERROR` cases retry with bounded backoff (`INFRA_MAX_RETRIES=2`, delays 2 s then 6 s). Every
retry counts against the 60-request cap. `LLMOutputError` is not retried (it is a finding about the model,
not the service).

**Preflight** (live mode only, zero model requests): the runner checks runtime presence, `get_auth_status()`
(`isAuthenticated`), and that the configured model id is in the built-in catalog. Any failure stops the run
before it spends a request and reports `INVALID` with the infrastructure cause.

## (c) Runtime download and corporate proxy / CA on macOS

Observed on this machine: `uv pip install` from PyPI and `python -m copilot download-runtime` both
**succeeded** without extra configuration (runtime `1.0.105` cached under
`~/Library/Caches/github-copilot-sdk/cli/1.0.105/prebuilds/darwin-arm64/`; the SDK verifies it against the
release `SHA256SUMS.txt`). A `copilot` CLI `1.0.101` is also installed through nvm, but it does not match
the SDK's pinned runtime version and is not used by default.

**Decision**: the harness setup step runs `python -m copilot download-runtime` once, before any live
request, so a download problem is reported as an infrastructure failure up front rather than inside a case.
If it fails on another network (for example a Microsoft Entra `BssoInterrupt` HTML page returned instead of
the archive, or a TLS error), the documented fallbacks, in order, are:

1. Export the corporate root and issuing CAs from the macOS keychain into a PEM bundle and set
   `SSL_CERT_FILE` (httpx uses it) for the download only; never disable TLS verification.
2. Download the platform archive in a signed-in browser, place the extracted runtime anywhere, and set
   `COPILOT_CLI_PATH` plus `COPILOT_SKIP_CLI_DOWNLOAD=1`.
3. Mirror the release assets and set `COPILOT_CLI_DOWNLOAD_BASE_URL`.

Authentication on this machine is the logged-in GitHub user (`get_auth_status` returned
`authType: gh-cli`), so no token is required locally. For unattended runs, `GH_TOKEN` /
`COPILOT_GITHUB_TOKEN` go in `.env` and are read only by `settings.py`; the harness redacts their values from
every captured output and `gitleaks` scans for them.

## (d) Model choice and request cost against the 60-request cap

Spike results (each row one live request; "served" is `assistant.usage.data.model`):

| Requested | Effort | Served | Result | Latency |
|-----------|--------|--------|--------|---------|
| `gpt-5-mini` | low | `gpt-6-luna` | OK | 6.9 s |
| `gpt-4.1` | none | `mai-code-1.1-flash` | OK | 6.4 s |
| `gpt-5.4-mini` | low | not captured | OK | 12.2 s |
| `claude-haiku-4.5` | none | `mai-code-1.1-flash` (second run) | OK | 8.6 s |
| `not-a-model` | none | `mai-code-1.1-flash` | OK (silent fallback) | 6.7 s |
| `gpt-6-luna` | low | `mai-code-1.1-flash` | OK | 9.9 s |
| `mai-code-1.1-flash` | none | `mai-code-1.1-flash` | OK | 9.6 s |
| `mai-code-1.1-flash` | low | `mai-code-1.1-flash` (twice) | OK | 9.9 s, 8.0 s |

Findings that change the design:

- The runtime does **not** reject an unknown model id and does not always serve the requested one. A
  fixed model id therefore cannot be assumed; the **served** model must be read from the event stream and
  compared with the configured id on every call. A mismatch is classified `INFRA_ERROR(model_routing)`
  (the service did not provide the contracted model) and is reported separately.
- `mai-code-1.1-flash` is in the `LOW` price category, served itself in 4 of 4 calls, accepted
  `reasoning_effort="low"`, and answered the structured schema correctly.
- Every request reported `cost = 1.0`, so cost cannot separate the cheap candidates; the price category and
  stability do.

**Decision**: `MODEL_ID=mai-code-1.1-flash`, `REASONING_EFFORT=low`, default in `settings.py`, asserted by the
harness through `EVAL_EXPECTED_MODEL_ID` in `.harness/config/thresholds.env` (checksummed, so changing the
model to chase a score is visible). Residual risk: model availability and routing depend on the account and
can change; the spike must be repeated (and the id re-pinned through a reviewed change) if preflight fails.

**Request budget** (hard cap 60 per full live run, counter in the runner, retries included):

| Component | Requests |
|-----------|----------|
| Planned dataset: 33 cases, of which 4 never reach the model (FR-8: too long, empty, whitespace, non-text) | M = 29 |
| FR-9 consistency: 8 designated cases run 2 extra times (run 1 is the scored run) | 8 x 2 = 16 |
| Base total | 45 |
| Reserve for `INFRA_ERROR` retries | 15 |
| **Cap** | **60** |

When the counter reaches 60 the runner stops, marks unrun cases `NOT_RUN`, and the verdict is `INVALID`.
At about 9 s per request sequentially, a full run is about 6 to 9 minutes; the runner uses a concurrency of
at most 2 (a shared client, a fresh session per request).

## (e) FR-9 repeat-run strategy

The SDK exposes no temperature, so run-to-run variation is controlled by: a fixed model id verified per call,
`reasoning_effort="low"`, a closed response schema, a deterministic prompt (including a precomputed reference
calendar, see (f)), and a fresh session per call with no memory.

**Decision**: 8 designated consistency cases (the ones with a single correct instant or target: AC-1, AC-2,
AC-17, AC-20, AC-22, AC-26, AC-35, AC-37) run **3 times** (`CONSISTENCY_K=3`). Run 1 is the scored run for all
three layers; runs 2 and 3 only feed the FR-9 check. FR-9 is a Layer 2 property of those cases: `intent`,
`datetime_iso` (compared as an instant) and `target_reminder_id` MUST be identical in all 3 runs. If a run is
`INFRA_ERROR` it is retried; if it cannot be completed the consistency check for that case is `NOT_RUN`
and counts as an `INFRA_ERROR` case. The per-case run count is written to `eval-results.json` (FR-15).

**Alternatives considered**: repeating every case 3 times (rejected: 78+ requests, over the cap); a single run
with a majority vote (rejected: hides the variance that FR-9 exists to expose).

## (f) Reproducible "now", timezones, and DST

**Decision**:

- A `Clock` Protocol with `SystemClock` (default) and the request's `now` (an aware ISO-8601 datetime) as the
  injected value. The service never calls `datetime.now()` itself, so tests and eval cases are reproducible.
- Timezones come from the standard library `zoneinfo` with the `tzdata` package pinned, so results do not
  depend on the operating-system database. An unknown key is a validation error (never a silent UTC
  fallback); an omitted timezone means `UTC`.
- The model is not asked to do calendar arithmetic unaided. The prompt builder deterministically adds a
  **reference calendar** to the system message: the local `now`, its weekday, and the next 14 local dates
  with weekday name and UTC offset, plus an explicit line for any date on which the offset changes (for
  example "2027-03-14: offset changes -05:00 -> -04:00; local times 02:00-02:59 do not exist"). The fixed
  windows (morning 09:00, afternoon 14:00, evening 18:00, night 21:00, end of day 17:00) and the weekday rules
  from the clarified spec are stated as rules in `prompts/system.md`.
- The validator enforces, from the model output alone and without natural-language parsing: the datetime is
  aware (INV-3); it is strictly after `now` (FR-1/FR-4); its offset equals the zone's offset at that instant
  (FR-1); its wall-clock time exists exactly once in the zone (a gap or a repeated hour is rejected, which is
  the deterministic backstop for the daylight-saving clarification rule). Whether the model should have asked
  a clarification instead is a model-behaviour property checked by Layer 2 of the eval, not by runtime code.
- Instants are compared in UTC everywhere (eval accuracy within 60 s, FR-9 equality); the offset text is only
  checked by FR-1.

## Additional decisions that affect the plan

- **Function length**: Ruff has no "lines per function" rule (`PLR0915` counts statements). `.harness/lint.sh`
  therefore runs a small AST check, `check_function_length.py`, reading `FUNC_LEN_MAX` from
  `thresholds.env`; Ruff `C901` handles complexity with `COMPLEXITY_MAX` injected on the command line.
- **Architecture rules are tested, not just reviewed**: an AST import-graph test asserts the one-way
  layering and that only `copilot_client.py` imports `copilot`; a fake-SDK test asserts the least-privilege
  session keywords and the deny-all handler.
- **One client, one session per request**: `CopilotClient` is created once per process (the runtime is
  expensive to start); every request creates and disconnects its own session with its own empty temporary
  working directory. The `base_directory` is a temporary directory removed at shutdown.
- **Layout conflict resolved in favour of the constitution**: the request asked for `src/app/...` and
  `tests/{unit,contract}`; the constitution requires `src/backend`, `tests/backend`. The plan uses
  `src/backend/app/{api,services,llm,models}` and `tests/backend/{unit,contract}`. See Complexity Tracking.
- **IDs**: the model never supplies a new reminder id. The repository mints ids for newly created reminders;
  every id the application *references* (reschedule, snooze, cancel) must already exist in the supplied list
  (INV-5, Principle VIII).
- **Payload size**: text longer than 1000 characters must produce `refuse` (`too_long`) (FR-8), so the request
  schema does not cap `text`; a transport-level body limit (1 MiB) returns `413` for abusive payloads.
