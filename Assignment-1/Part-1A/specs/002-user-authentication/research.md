# Research: User Authentication for Bus Booking

All technical unknowns are resolved. Format: Decision, Rationale, Alternatives considered. Items marked **Verified**
were checked on this machine while planning (FastAPI 0.162.0 in the root `.venv`; wheels downloaded without
installing).

## 1. Password hashing

- **Decision**: Argon2id through `argon2-cffi` (`argon2.PasswordHasher`). The hash string carries its own salt and
  cost parameters, so verification works for hashes made with other parameters.
- **Rationale**: The constitution (VII) allows bcrypt or argon2. The spec accepts passwords of up to 128 characters
  (FR-008) and says they are compared "without alteration" (edge case). bcrypt only uses the first 72 bytes, so two
  long passwords with the same first 72 bytes would both succeed; Argon2id has no such limit. **Verified**:
  `argon2_cffi-25.1.0` (pure Python) and `argon2_cffi_bindings-26.1.0-cp310-abi3-macosx_11_0_arm64` download as
  binary wheels, so no compiler is needed behind the corporate proxy.
- **Cost**: library defaults (time 3, memory 64 MiB, parallelism 4) are expected to take well under the 500 ms
  sign-in budget (NFR-005); the performance test measures it, and the cost parameters are settings-free constants in
  one module so they can be tuned if the measurement fails. Tests build the hasher with minimal cost (time 1,
  memory 8 MiB) so the suite stays fast; production-cost hashes still verify because parameters are stored in each
  hash.
- **Alternatives**: `bcrypt` (72-byte limit; would need a pre-hash step); `passlib` (unmaintained, and brings bcrypt
  compatibility problems); `hashlib.scrypt` (standard library, but hand-built encoding of salt and parameters is
  error-prone).

## 2. Session credential: signed token plus a server-side session row

- **Decision**: Sign-in creates a row in a new `sessions` table and returns a signed JWT (HS256, `PyJWT`) whose claims
  are `sid` (session id), `sub` (user id), `iat`, and `exp`. A request is accepted only if (1) the signature is valid,
  and (2) the session row exists, is not ended, and has not expired, judged by the injected `Clock` (not by the
  library's clock). Sign-out sets `ended_at`.
- **Rationale**: The constitution (VII) requires "short-lived signed tokens"; the spec requires that a signed-out
  credential is refused at once everywhere (FR-022, NFR-007) and that the server keeps no sign-in state in memory
  (NFR-009). A purely stateless JWT cannot be revoked; a purely opaque random id is not a signed token. The hybrid
  satisfies both: the signature rejects forged or altered credentials without a database call, and the row makes
  sign-out and expiry authoritative. The token is signed with `JWT_SECRET` (named in constitution VI), required at
  startup and at least 32 characters.
- **Hardening**: decode with `algorithms=["HS256"]` pinned (rejects `alg: none` and algorithm confusion), require
  the `sid`, `sub`, `iat`, `exp` claims, and set `verify_exp=False` because expiry is decided by the service with the
  injected clock (this also makes the 30-minute boundary testable without sleeping).
- **Alternatives**: opaque random token stored in the database (simplest, but not "signed" as the constitution
  demands); JWT with no session row (cannot satisfy sign-out); `itsdangerous` (fine, but PyJWT is the common standard
  and the claims map is self-describing); refresh tokens (out of scope: no extension of sessions).

## 3. Where the credential travels and where the browser keeps it

- **Decision**: `Authorization: Bearer <token>` header on every protected call. The SPA keeps the token in
  `sessionStorage`, which is per tab, survives a reload in the same tab, and is erased when the tab closes.
- **Rationale**: This is exactly the clarified behaviour (spec Clarifications, answer A: sign-in belongs to one tab).
  A header (not a cookie) is never sent automatically by the browser, so there is no cross-site request forgery
  surface and no `SameSite` or CSRF-token machinery to build. The token never appears in a URL.
- **Accepted risk**: script injected into the page could read `sessionStorage`. The UI renders only escaped React
  output and has no HTML injection points; a Content-Security-Policy header is a production hardening item outside
  this local mock scope (recorded in Missing Steps).
- **Alternatives**: `localStorage` (shared across tabs and survives browser restarts: contradicts the clarification);
  an `HttpOnly` cookie (shared across tabs: contradicts the clarification; needs CSRF protection).

## 4. Enforcing "no bypass": three layers

- **Verified fact**: with a dependency guard on a route, a well-formed but invalid body returns the guard's `401`
  (the guard runs before field validation), but a body that is not valid JSON returns `422` because FastAPI parses
  the JSON before it resolves dependencies (checked: `bad schema -> 401`, `bad json -> 422`). The spec requires `401`
  before any body processing (User Story 2, scenario 3; FR-014).
- **Decision**:
  1. **Gate middleware (default deny, stateless)**: a pure ASGI middleware runs before routing. For every request that
     matches a registered `/api/v1` route and is not one of the public routes, it requires a bearer token with a valid
     signature; otherwise it answers `401 unauthenticated` without parsing the body. Public routes are read from one
     `public_router` object (sign-in and the two health checks), so the allow-list cannot drift from the code, and any
     route added anywhere else is protected by default (FR-017). Paths that match no route fall through to the normal
     `404`, so the retired user list still answers `404` signed in or not.
  2. **Router dependency (authoritative)**: every non-public router is mounted on a `protected_router` created with
     `dependencies=[Depends(require_session)]`. It loads the session and user through `AuthService.authenticate` and
     checks the row and the expiry. Handlers needing the caller ask for `CurrentUser`.
  3. **Enumeration test**: a test walks every route of the built app, calls it with no credential, with a forged
     credential, and with a signed-out credential, and fails if any route outside the public list does not return
     `401` (SC-003). A route added without protection would fail this test and the gate in layer 1.
- **Rationale**: layer 2 is the constitution-conformant place for business-side checks (services get repositories
  through `Depends`); layer 1 exists only because of the verified body-parsing order and doubles as default deny. The
  gate does no database work, so it adds no latency worth measuring (NFR-006).
- **Alternatives**: a dependency only (fails the malformed-JSON case, would require weakening the spec); a middleware
  that does the whole check (cannot receive the `Depends`-built service, so it would instantiate concrete classes
  inline, which Principle I forbids, and would query twice); a custom `APIRoute` subclass (reorders nothing, since
  body parsing is inside the route handler it wraps).

## 5. Failures that must be stored (sign-in attempts)

- **Decision**: `AuthService.login` returns a value (`LoginSuccess` or a `LoginRejected` carrying a domain error)
  instead of raising. The route converts a rejection into the error response through one function in
  `error_handlers.py` (`response_for(error)`), which the exception handler also uses.
- **Rationale**: the request session is a `scope="function"` dependency that rolls back when the endpoint raises (see
  `api/deps.py`). A raised `InvalidCredentialsError` would also erase the failure record that throttling and the
  audit trail (FR-011, FR-026) depend on. Returning the rejection lets the transaction commit the attempt row, and
  error text is still produced only in the error-handler module (Principle IV).
- **Alternatives**: a second, independent database session for audit rows (two transactions per request, extra
  connection, and the same rollback problem if its dependency sees the exception); catching and re-raising after
  commit inside the service (the service would own the transaction, which breaks the layering).

## 6. Exact username match on SQL Server

- **Decision**: look the user up by username in SQL, then require `user.username == supplied` in Python before
  verifying the password. The `users.username` column keeps the default collation and a unique constraint.
- **Rationale**: SQL Server's default collation is case-insensitive and ignores trailing spaces in comparisons, so
  `ASHA` and `asha ` would match `asha` in SQL. The spec requires exact matching (FR-006). The Python comparison
  makes the rule independent of the collation. The unique constraint also stops two usernames that differ only by
  case.
- **Note on throttling**: the attempt-count query deliberately uses the database comparison, so `ASHA`, `asha` and
  `asha ` share one failure count and a guesser cannot dodge the block by changing case (this counts the real user
  `asha` as failing, which is the intended per-username block).
- **Alternatives**: a case-sensitive binary column collation (works, but makes the schema non-portable to engines
  without that collation name and still leaves trailing-space equality); lower-casing input (spec says no).

## 7. Uniform failure and timing

- **Decision**: every rejected sign-in goes through the same code path: unknown username, wrong password, and wrong
  pair all run one Argon2 verification (against the stored hash, or against a fixed dummy hash created at start-up when
  the user does not exist) and return the same `401 invalid_credentials` body. The throttle check happens first and
  is identical for existing and unknown usernames.
- **Rationale**: FR-007 and NFR-003 (identical bodies; p95 times within 50 ms across 1,000 failures). Skipping the
  hash for unknown users would make them measurably faster.
- **Alternatives**: constant-time sleeps (add latency, not reliably equal); only comparing messages (leaks timing).

## 8. Throttling design

- **Decision**: a `sign_in_attempts` table with one row per sign-in success, failure, throttled attempt and sign-out
  (this is also the audit trail, FR-011/NFR-012). A username is throttled when it has at least 5 `failure` rows
  newer than `max(now - 5 minutes, its latest success)` and `now < latest failure + 60 seconds`. `throttled` and
  `signout` rows never count as failures, so a blocked guesser cannot extend the wait by trying more.
  The response is `429 too_many_attempts` with the seconds left in the message and a `Retry-After` header.
- **Rationale**: matches FR-026/FR-027 and the clarified answer (per-username block). It is stateless (state in the
  database, NFR-009) so it works across any number of server instances. An index on `(username, attempted_at)`
  serves the only query.
- **Known limits (accepted for the mock scenario)**: two simultaneous wrong guesses can slip one extra attempt past
  the count (no row lock); someone who knows a username can keep that user waiting 60 seconds at a time (spec
  Assumptions); attempted usernames are stored as typed, so a password mistakenly typed into the username field is
  stored for at most 50 characters in the audit table (never logged, never returned).
- **Alternatives**: in-memory counters (state in the server, breaks stateless scaling); per-client-address limits
  (clarified answer rejects them); progressive delay (spec requires a block).

## 9. Mock credentials without secrets in source

- **Decision**: the mock passwords live only in the git-ignored `.env`, as one setting
  `MOCK_USER_PASSWORDS={"asha":"...","ravi":"...","meera":"..."}` (JSON map, parsed by `pydantic-settings` into
  `dict[str, SecretStr]`). Only the seed command reads it; the running API never needs it, so it is optional at
  server start-up but the seed refuses to run (naming the missing usernames, never values) when a seeded user has no
  entry. The tests never read it: they generate a random password per user per test session and seed with that.
  `.env.example` lists the names with placeholders.
- **Rationale**: constitution VI forbids passwords in source, tests, fixtures, seed data, logs and evidence; adding a
  user is one seed row plus one `.env` entry (no code change, as feature 001 designed). Random test passwords mean the
  test suite carries no credential at all and cannot be used to guess the developer's `.env` values.
- **Alternatives**: one variable per user (`MOCK_PASSWORD_ASHA`, requires a code change per user); a committed
  seed file with hashes (publishes a crackable value, and tests would need the plain text anyway); a shared default
  password (violates VI and defeats "only the right combination").

## 10. Schema change on a populated table

- **Decision**: Alembic migration `0002_add_authentication` adds `users.username` and `users.password_hash` as
  nullable, back-fills existing rows (`username = LOWER(name)`, `password_hash = '!'`), then makes both NOT NULL and
  adds the unique and check constraints; it also creates `sessions` and `sign_in_attempts`. The marker `'!'` is not a
  valid Argon2 string, so every user is locked out until the seed command (always part of `db-init.sh`) writes real
  hashes. The migration holds no password and no hash.
- **Rationale**: a plain `ADD COLUMN ... NOT NULL` fails on an existing table; an invented default password would be a
  hidden credential. Failing closed is the safe default, and it is testable (migration test on a scratch database).
  Downgrade drops the new tables and columns, so the migration is reversible.
- **Alternatives**: edit `0001` (forbidden: constitution VIII, versioned migrations only; databases already exist);
  require an empty table (breaks `db-init.sh` on an existing `bus_db`).

## 11. Booking identity comes from the session; the user list is removed

- **Decision**: `BookingCreate` no longer has `user_id`; with `extra="forbid"` a body that includes it returns `422`.
  `POST /bookings` passes the session's user id to `BookingService.book_seats`. The `UserReader` dependency,
  `UserNotFoundError`, the `/users` router, `UserService`, `UserOut`, and the frontend `UserSelect`, `useUsers`,
  `api/users.ts` are deleted (clarified answer: the list-users operation is removed).
- **Rationale**: FR-019 and FR-021; fewer endpoints and no way to ask who else exists (FR-018). The foreign key keeps
  `bookings.user_id` valid, and a session can only be for an existing user, so the service no longer needs the check.
- **Alternatives**: keep `user_id` and compare it with the session (an identity field the client can always get
  wrong; the spec says it must be rejected).

## 12. Frontend authentication state

- **Decision**: a small auth state machine in a hook (`useAuthSession`): `checking` (on load, only when a token is
  present, call `GET /auth/me`), `signedIn(user)`, or `signedOut(reason)` where reason is `none`, `expired`, or
  `signedOut`. An `AuthProvider` exposes it through context; `RequireAuth` wraps the protected routes and renders
  nothing but a loading line until the state is known; `AppHeader` shows the name and the Sign out control.
  `api/client.ts` adds the header and, when a protected call returns `401` with code `unauthenticated`, calls the
  session store's `expire()`; the provider reacts by returning to `/login` with the expiry message.
- **Rationale**: the user's name always comes from the server (`/auth/me`), never from browser-held data, so editing
  `sessionStorage` cannot make the UI claim a user (spec User Story 2, scenario 6). Only `api/session.ts` touches
  `sessionStorage`, and components still never call `fetch` (Principle I; an architecture test covers both rules).
  The login error code `invalid_credentials` is not treated as an expired session, because the code differs.
- **Alternatives**: store the user object in `sessionStorage` (trusts the client); React Router loaders (new data
  layer, not used elsewhere); a state library (new dependency without need).

## 13. Response caching and CORS

- **Decision**: a tiny middleware adds `Cache-Control: no-store` to every `/api/v1` response so a browser does not
  keep bus or seat data after sign-out; the CORS configuration adds `authorization` to the allowed request headers
  (methods stay `GET`, `POST`; origins stay the configured list, never a wildcard).
- **Rationale**: spec User Story 4, scenario 3 (no data after Back); without `authorization` in the allow-list a
  cross-origin browser would block the header.
- **Alternatives**: rely on default heuristics (not guaranteed).

## 14. Evidence and branch layout for a second feature

- **Decision (needs human confirmation at the approval gate)**: do this feature on branch `002-user-authentication`.
  Feature 001's recorded evidence stays untouched on `main` and under the tag `initial-generation`. On the feature
  branch, archive it with `git mv` into `evidence/001-seat-booking/` (log, results, both generations) so that the
  runner, which writes to `evidence/harness-results/` and appends to `evidence/harness-log.md`, starts clean for
  this feature. Tag the first generation `002-initial-generation` (the name `initial-generation` is taken) and
  snapshot it to `evidence/initial-generation/`.
- **Rationale**: `.harness/run.sh` is protected and has those paths built in; changing it for one feature would need
  a visible checksum change. Archiving is a move, not an edit, and the accepted 001 submission stays intact on
  `main`.
- **Alternatives**: append feature 002 sections to the 001 log (breaks the constitution's required section order
  because the run table of 001 would no longer be last); give `run.sh` an output-folder option (edits a protected
  script); overwrite `evidence/` (destroys accepted evidence).

## 15. Secret redaction in harness evidence

- **Fact found**: `.harness/redact.sh` redacts only the value of `DB_PASSWORD`. `JWT_SECRET` and the mock passwords
  would not be masked if a failing test printed them.
- **Decision**: (a) tests never print credentials (assertion messages carry names and status codes, never the token
  or the password; a unit test asserts the plain test passwords and the token never occur in captured responses and
  log records); (b) as defence in depth, extend `redact.sh` to also mask `JWT_SECRET` and every
  `MOCK_USER_PASSWORDS` value, with its unit test and a regenerated `checksums.sha256`. Item (b) edits a protected
  file, so it is a separate task that needs explicit human approval before it runs.
- **Alternatives**: do nothing (relies on discipline alone); move redaction into pytest only (does not cover
  Playwright or lint output).

## 16. What is intentionally not done

- Production TLS: tokens travel over plain HTTP in local development; any real deployment must terminate TLS (the
  constitution already says the mock-user exemption ends "before any real use").
- Session clean-up job: expired `sessions` and old `sign_in_attempts` rows are not deleted automatically (the seed
  resets them; a retention job is a later feature).
- Password rules, rotation and reset: out of scope per the spec.
- Content-Security-Policy header: production hardening, recorded in the plan's Missing Steps.
