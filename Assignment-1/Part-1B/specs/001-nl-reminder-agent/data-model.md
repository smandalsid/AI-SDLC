# Data Model: Natural-Language Reminder Agent

Derived from [spec.md](spec.md). Field names match the spec's output contract exactly. All Pydantic models use
`extra="forbid"`. Types are described without code.

## Request side

### InterpretRequest (HTTP body)

| Field | Type | Rule |
|-------|------|------|
| `text` | string (strict; a number, null, list, or object is rejected) | required; not empty and not whitespace-only (422). No maximum at the schema level: over 1000 characters is accepted here and refused by `text_guard` with `refuse` / `too_long` (FR-8). Exactly 1000 is processed |
| `timezone` | string | IANA key accepted by `zoneinfo` (with `tzdata`); default `UTC`; unknown key gives 422 and is never replaced silently |
| `now` | ISO-8601 datetime with UTC offset | optional; when omitted `Clock.now()` is used. A naive datetime gives 422 |
| `reminders` | list of `ReminderIn` | default empty; at most 200 items; ids must be unique |

### ReminderIn

| Field | Type | Rule |
|-------|------|------|
| `id` | string | 1 to 64 characters, pattern `^[A-Za-z0-9_-]+$`; unique within the list. The only source of valid target ids (INV-5) |
| `title` | string | 1 to 120 characters |
| `time` | ISO-8601 datetime with UTC offset | required |

Instructions that appear inside `title` are data. The title is JSON-encoded into a delimited data block and the
system prompt says so (spec edge case; G06).

### CallerContext (internal, built per call)

`zone` (a `ZoneInfo`), `now_utc`, `now_local` (derived from `now` and `zone`), and the supplied reminders.
Nothing is read from the process clock inside the service.

## Model side

### ProposedActionWire (what the SDK is asked to return)

The eight spec fields with plain types and no constraints, all required, `extra="forbid"`:
`intent` (enum of 6), `title` (string or null), `datetime_iso` (string or null), `snooze_minutes` (integer or
null), `target_reminder_id` (string or null), `clarification_question` (string or null), `refusal_reason`
(enum of 5 or null), `confidence` (number). `evals/output-schema.json` is authored by hand from the spec's Output
Contract (it is a spec artifact, checksummed from the start, not generated from code); the Layer 1 evaluator
validates against it, and a unit test checks that this model and `ProposedAction` agree with it.

### ProposedAction (validated domain model; the contract returned to callers)

Same eight fields, with the spec's ranges enforced by the application:

| Field | Rule |
|-------|------|
| `intent` | one of `create`, `reschedule`, `snooze`, `cancel`, `clarify`, `refuse` (INV-2) |
| `title` | 1 to 120 characters or null |
| `datetime_iso` | ISO-8601 with an explicit UTC offset or null (INV-3) |
| `snooze_minutes` | integer 1 to 1440 or null (INV-4) |
| `target_reminder_id` | string or null; when set it must exist in the supplied list (INV-5, checked by the validator because it needs the request) |
| `clarification_question` | non-empty, at most 200 characters, present if and only if `intent` is `clarify` (INV-6) |
| `refusal_reason` | one of `unsafe`, `injection`, `out_of_scope`, `bulk_action`, `too_long`; present if and only if `intent` is `refuse` (INV-7) |
| `confidence` | number from 0 to 1 |

Required fields per intent (cross-field validation in the model):

| Intent | Required |
|--------|----------|
| `create` | `title`, `datetime_iso` |
| `reschedule` | `target_reminder_id`, `datetime_iso` |
| `snooze` | `target_reminder_id`, `snooze_minutes` |
| `cancel` | `target_reminder_id` |
| `clarify` | `clarification_question` |
| `refuse` | `refusal_reason` |

Fields an intent does not require may be null (spec assumption); the applier reads only the fields that apply
to the intent, so an extra populated field has no effect.

### Validator rules (services/validator.py; applied after the model parses)

| Rule | Spec | Failure |
|------|------|---------|
| `target_reminder_id` is one of the supplied ids | INV-5 | `LLMOutputError` (`unknown_target`) |
| for `create` and `reschedule`: `datetime_iso` is strictly after `now` | FR-1, FR-4 | `LLMOutputError` (`not_future`) |
| its offset equals the zone's offset at that instant | FR-1 | `LLMOutputError` (`offset_mismatch`) |
| its wall-clock time exists exactly once in the zone (not in a daylight-saving gap, not in a repeated hour) | FR-1, spec clarification | `LLMOutputError` (`nonexistent_or_ambiguous_time`) |
| no output string contains a sentinel (system-prompt canary phrases, configured secret values) | GR-4 | `LLMOutputError` (`leak`) |

A failure never yields a partial action: the API returns a controlled error and the applier does not run (GR-5).

## Result side

### AppliedResult

| Field | Type | Meaning |
|-------|------|---------|
| `operation` | `created`, `rescheduled`, `snoozed`, `cancelled`, `none` | `none` for `clarify` and `refuse` |
| `affected_id` | string or null | id of the single reminder touched; new reminders get an id minted by the store, never by the model |
| `new_time` | datetime or null | for `snoozed`: target time plus `snooze_minutes`, or `now` plus `snooze_minutes` if the target time has passed (FR-6) |
| `reminders` | list of `{id, title, time}` | the in-memory state after applying the action |

### InterpretResponse (HTTP 200)

`{"action": ProposedAction, "applied": AppliedResult}`. `clarify` and `refuse` (including `too_long`) are
successful responses, not errors.

## Services state

### ReminderStore (Protocol) and InMemoryReminderStore

Operations: `list()`, `add(title, time) -> id`, `set_time(id, time)`, `remove(id)`. Seeded from the request's
reminders; discarded after the call (the agent keeps no memory between calls). Lifecycle of one reminder in a
call: absent, then `created`; or present, then `rescheduled` or `snoozed` (time changes, id and title do not);
or present, then `cancelled` (removed). Exactly one reminder changes per call (FR-7); `remove` of an unknown id
is a programming error because the validator has already checked INV-5.

### LLMRequest and CallRecord

`LLMRequest`: `system_prompt` (text), `user_message` (JSON-encoded data block), `correlation_id` (case id and run
index in the harness; a random id in the API). `CallRecord` (passed to an optional sink, used by the harness
for FR-15): `model_requested`, `model_served`, `reasoning_effort`, `input_tokens`, `output_tokens`, `duration_ms`,
`attempt`. It never contains the prompt text, tokens, or secrets.

`PreflightResult` (returned by `Preflight.preflight()`, a separate small Protocol implemented by the SDK adapter,
zero model requests): `runtime_ok`, `authenticated`, `model_in_catalog`, `runtime_version`, `sdk_version`.

## Errors (models/errors.py)

Every error becomes `{"error": {"code": str, "message": str}}` through the single handler in `api/errors.py`.

| Exception | HTTP | `code` | Spec |
|-----------|------|--------|------|
| `RequestValidationFailed` (schema, empty or whitespace text, non-text, unknown timezone, naive `now`, duplicate ids) | 422 | `invalid_request` | FR-8 |
| `PayloadTooLarge` (transport body limit, 1 MiB) | 413 | `payload_too_large` | plan decision |
| `LLMOutputError` (schema or validator failure) | 502 | `model_output_invalid` | GR-5 |
| `LLMInfrastructureError` kind `timeout` | 504 | `llm_timeout` | FR-14 |
| `LLMInfrastructureError` other kinds | 503 | `llm_unavailable` | FR-14 |
| any other exception | 500 | `internal_error` | no internals leaked |

## Evaluation entities (detail in [contracts/](contracts/))

- **EvalCase**: `id`, `category` (normal, boundary, ambiguous, missing_info, malformed, adversarial),
  `input` (text or non-text value, timezone, now, reminders), `traces` (requirement ids, at least one),
  `consistency` (boolean), `expected` (ground truth, deterministic properties, or a rubric).
- **EvalCaseResult**: `case_id`, `status` (`PASS`, `FAIL`, `INFRA_ERROR`, `NOT_RUN`), `runs` (count), per-layer
  scores, per-check outcomes with requirement ids, the observed action, and the `CallRecord` summary.
- **EvalRunSummary**: per-layer pass rate, per-category scores, aggregate, INFRA share, request count, verdict.
