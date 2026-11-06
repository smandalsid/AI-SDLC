# Quickstart: User Authentication

Validation guide for the feature once implemented. Contract: [contracts/openapi.yaml](contracts/openapi.yaml). Data:
[data-model.md](data-model.md). Feature 001's quickstart still applies for tools, ports and the one-time setup; only the
differences are listed here.

## Prerequisites (new)

1. Two new entries in the git-ignored `.env`. **You add these yourself; coding agents never write `.env`.**
   - `JWT_SECRET`: at least 32 random characters. Generate one in your own terminal and paste it into `.env`
     (do not paste it into chat or any committed file):
     `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `MOCK_USER_PASSWORDS`: one line of JSON mapping each seeded username to its mock password, for example
     `MOCK_USER_PASSWORDS={"asha":"<choose>","ravi":"<choose>","meera":"<choose>"}` (1-128 characters each).
   `.env.example` lists both names with placeholders only.
2. Install the two new Python dependencies (already installed): `PyJWT` and `argon2-cffi` through `uv` into the root `.venv`,
   lock file committed.

## Create or upgrade the development database

```bash
scripts/db-init.sh
```

Expected output: creates `bus_db` if missing, applies migrations `0001` and `0002` (an existing `bus_db` is upgraded in
place; existing users get `username = lower(name)` and a locked placeholder hash), then the seed resets the data:
3 buses, 3 users with usernames `asha`, `ravi`, `meera` and real Argon2id hashes made from `MOCK_USER_PASSWORDS`,
0 bookings, 0 sessions, 0 sign-in records. If a user has no entry in `MOCK_USER_PASSWORDS` the seed stops and names
the usernames that are missing (never values). Running it again gives the same end state and ends all sessions.

Check the schema in a SQL client or with the integration tests: `users` has `username` and `password_hash`;
`sessions` and `sign_in_attempts` exist.

## Run the application

```bash
scripts/dev.sh
```

Open http://localhost:5173. The backend refuses to start if `JWT_SECRET` is missing or shorter than 32 characters.

## Validation scenarios (API)

Enter the password without echoing it, then sign in. The username is `asha`.

```bash
read -rs ASHA_PW
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' \
  -d "{\"username\":\"asha\",\"password\":\"$ASHA_PW\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

1. **Sign in (US1)**: the call returns 200 with `access_token`, `token_type` `bearer`, `expires_at` (30 minutes ahead),
   and `user` (`id` 1, `name` "Asha"). The response has no password or hash.
2. **Wrong credentials (US1)**: a wrong password for `asha`, the password of `asha` sent for `ravi`, and an unknown
   username all return the identical 401 body `{"error":{"code":"invalid_credentials",...}}`. `ASHA`, ` asha` and
   `asha' OR '1'='1` also return that 401. An empty field, a 129-character password, or an extra field returns 422.
3. **Protection (US2)**: without the header, `GET /buses`, `GET /buses/1`, and `POST /bookings` (even with a valid body,
   and even with malformed JSON) return 401 `unauthenticated` and store nothing; `GET /users` returns 404. With a token
   that has one character changed, also 401. `GET /health` and `GET /health/ready` work without a token.
4. **Book as the signed-in user (US3)**:
   `curl -s -X POST localhost:8000/api/v1/bookings -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"bus_id":1,"seat_numbers":[3,4]}'`
   returns 201 with `user_id` 1. The same body plus `"user_id":2` returns 422 and stores nothing. Sign in as `ravi` in
   another shell and book seat 5: that booking has `user_id` 2.
5. **Sign out (US4)**: `curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/api/v1/auth/logout -H "authorization: Bearer $TOKEN"`
   prints 204; repeating any protected call with the same `$TOKEN` prints 401, as does a second sign-out. Signing in
   again returns a new token that works; the old one stays refused.
6. **Expiry (US5)**: not practical by hand (30 minutes); it is covered by tests that control the clock. To see it live,
   leave the UI open for 30 minutes and click a bus: you are returned to sign-in with "Your session has expired.
   Please sign in again."
7. **Throttle (US6)**: five wrong passwords for `asha` in a row, then the right one: the sixth call returns 429
   `too_many_attempts` with a `Retry-After` header and the seconds in the message; `ravi` can still sign in; after 60
   seconds `asha` can sign in. Run `scripts/db-init.sh` to clear the counters.

## Validation scenarios (UI)

1. Open http://localhost:5173/buses/1 in a new tab: the sign-in screen appears and no bus data flashes.
2. Enter a wrong password: a generic "Invalid username or password" message; the password field is masked.
3. Enter `asha` and her password: the bus list appears, the header shows "Asha" and a Sign out button; there is no user
   selector on the seat page.
4. Open Bus A, select seats 7 and 8, Confirm: success message; reload the tab: still signed in and the seats show booked.
5. Click Sign out: the sign-in screen appears; press the browser Back button: still the sign-in screen, no bus data.
6. Open the application in a second tab: it shows the sign-in screen (sign-in belongs to one tab).
7. In the browser developer tools set `sessionStorage` to a made-up token and reload: you are returned to sign-in, with the message "Your session has expired. Please sign in again." (a stored token the server does not accept is treated as an expired session).
8. Resize to 320 px: the sign-in screen and the header (name and Sign out) have no horizontal scroll.

## How the test database is populated (automated checks)

```bash
source .venv/bin/activate
scripts/db-test-init.sh          # optional manual refresh of bus_db_test (needs the .env entries above)
(cd src/backend && pytest)       # pytest does the steps below by itself
```

What pytest does, in order (see plan, "Test Database Population"):

1. Computes `bus_db_test` and refuses any name that does not end in `_test`.
2. Drops and recreates it, then runs `alembic upgrade head` (both migrations, so the tested schema is the real schema).
3. Generates one random password per seeded username (kept in memory for the session, never printed or written) and
   hashes them once with a minimal-cost Argon2 hasher.
4. Before every non-unit test, resets the data with those hashes: 3 buses, 3 users (`asha`, `ravi`, `meera`) whose
   passwords the tests know through the `credentials` fixture, empty bookings, sessions and sign-in records.
5. Tests sign in through the real endpoint (fixture `auth_headers("asha")`) so the full path is exercised; the fake
   clock fixture moves time to test the 30-minute boundary and the throttle window.

The migration test builds a scratch `*_test` database at revision `0001`, inserts the three 001 users, upgrades to
`0002`, and asserts the back-fill (usernames, locked hashes, nobody can sign in) and the downgrade.

```bash
(cd src/backend && pytest -m perf)   # sign-in p95 < 500 ms, protection overhead <= 50 ms
npm --prefix src/frontend test       # Vitest + RTL (login form, provider, route guard, header, client 401 handling)
npm --prefix src/frontend run e2e    # Playwright; signs in with the passwords from .env
.harness/run.sh                      # all gates
```

Playwright reads the same `MOCK_USER_PASSWORDS` from `.env` (the e2e backend seeds `bus_db_test` with them), so the
browser checks need no credential in source.
