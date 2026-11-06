# Feature Specification: User Authentication for Bus Booking

**Feature Branch**: `002-user-authentication`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "We have been working on a bus booking application (see the handoff notes, the code and the 001 spec). Now we want to enable authentication for a user to be able to book a bus. We do not want the complexity of sign up, update, or delete users: assume a mock username and password for every user, and use these for authentication. A user can log in only when they enter the right credentials. A user can book a bus seat only when logged in with the right credentials. The user must not be able to bypass authentication from the UI or from direct API calls in any way; only the right combination of user id and password is allowed. There must also be a sign-out option, after which the user must authenticate again to view buses and book tickets. Define user stories, functional and non-functional requirements, and acceptance criteria."

## Clarifications

### Session 2026-11-03

- Q: Should a sign-in be shared by all browser tabs and survive closing the browser, or belong to a single tab? → A: Per tab only (a sign-in survives a reload but ends when the tab is closed; other tabs are unaffected).
- Q: Should the 001 "list users" operation be removed or kept and protected? → A: Removed (the operation no longer exists; a call returns 404 whether signed in or not).
- Q: Should a session end a fixed 30 minutes after sign-in, or 30 minutes after last activity? → A: Fixed 30 minutes after sign-in, regardless of activity.
- Q: After 5 wrong passwords, should the username be blocked for everyone for 60 seconds, or only the client that failed? → A: Block the username for everyone for 60 seconds, including the right password (per-username throttle).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign in with the right credentials (Priority: P1)

A visitor opens the application and sees only a sign-in screen. They enter a username and password. If the combination matches one of the mock users, they are signed in and taken to the bus list. If it does not match, they stay on the sign-in screen with a generic error and nothing else is revealed.

**Why this priority**: Every other protected capability depends on being able to establish who the user is. It is the smallest independently demonstrable slice.

**Independent Test**: With the mock users loaded, submit Asha's username with Asha's password and verify the bus list appears; submit Asha's username with a wrong password and verify the sign-in screen stays with an error and no bus data is shown.

**Acceptance Scenarios**:

1. **Given** mock user "Asha" exists with username `asha`, **When** the visitor submits username `asha` with Asha's correct password, **Then** the sign-in succeeds (HTTP 200), the response identifies the signed-in user (identifier and display name) and carries no password or password-derived value, and the UI shows the bus list.
2. **Given** username `asha` exists, **When** the visitor submits `asha` with a wrong password, **Then** the sign-in is refused (HTTP 401) with the generic message "Invalid username or password", no session is created, and the UI stays on the sign-in screen.
3. **Given** no user has username `nobody`, **When** the visitor submits `nobody` with any password, **Then** the sign-in is refused (HTTP 401) with exactly the same message and the same response shape as scenario 2, so that existing and non-existing usernames cannot be told apart.
4. **Given** Asha's correct password belongs to `asha`, **When** the visitor submits username `ravi` with Asha's password, **Then** the sign-in is refused (HTTP 401); a password is valid only for its own user.
5. **Given** the sign-in screen, **When** the visitor submits an empty username or an empty password, **Then** the UI blocks the submit with a field-level message, and a direct request with an empty or missing field is rejected with a validation error (HTTP 422) and no session is created.
6. **Given** a sign-in request with a username longer than 50 characters or a password longer than 128 characters, **When** it is submitted, **Then** it is rejected with a validation error (HTTP 422) and no session is created.
7. **Given** a sign-in request containing any field other than username and password, **When** it is submitted, **Then** it is rejected with a validation error (HTTP 422).
8. **Given** a sign-in request whose username is `asha' OR '1'='1` or `ASHA` (different letter case) or ` asha` (leading space), **When** it is submitted with Asha's correct password, **Then** it is refused (HTTP 401); the username must match exactly.
9. **Given** the sign-in screen, **When** the visitor types a password, **Then** the characters are masked, and neither the username nor the password ever appears in a page address, a stored browser history entry, a log line, or an error message.

---

### User Story 2 - Buses and booking are unreachable without signing in (Priority: P1)

Nothing of the booking application is available to someone who is not signed in. This holds for every route in the UI and for every direct call to the API, however the call is crafted.

**Why this priority**: This is the point of the feature. A sign-in screen that can be bypassed is worse than none.

**Independent Test**: With no sign-in, call every API operation other than sign-in and the health checks and verify each is refused (HTTP 401) with no business data; open each UI address directly and verify the sign-in screen is shown.

**Acceptance Scenarios**:

1. **Given** no one is signed in, **When** a request lists buses or gets one bus with its seats, **Then** each is refused (HTTP 401) and the body contains no bus, seat, user, or booking data; a request to the retired user-list address returns 404 with no data, whether signed in or not.
2. **Given** no one is signed in, **When** a request registers a booking for an available seat, **Then** it is refused (HTTP 401) and no booking record is stored, even though the body is otherwise valid.
3. **Given** no one is signed in, **When** a request sends a malformed booking body to a protected operation, **Then** the response is 401 and not 422; authentication is checked before the body is examined, so an unauthenticated caller learns nothing about the validation rules.
4. **Given** a request carries a session credential that was never issued, that was altered by one character, that is empty, that is in the wrong form, or that was issued for a user who no longer exists, **When** it is sent to any protected operation, **Then** it is refused (HTTP 401) and no data is returned or changed.
5. **Given** no one is signed in, **When** the visitor opens the address of the bus list or of a bus's seat page directly in the browser, **Then** the sign-in screen is shown, no bus or seat data is displayed at any moment (not even briefly), and after a successful sign-in the visitor lands on the bus list.
6. **Given** no one is signed in, **When** the visitor edits browser-held data (for example, adds a made-up "signed in" flag or user name) and reloads, **Then** the application still shows the sign-in screen and the API still refuses protected calls (HTTP 401); the UI is a convenience and the server alone decides.
7. **Given** a protected call is refused, **When** the response is inspected, **Then** it uses the common error shape with the code `unauthenticated` and a generic message, and does not say whether the credential was missing, malformed, forged, or expired.
8. **Given** the complete set of operations the API exposes, **When** an automated check enumerates them, **Then** every operation other than sign-in and the two health checks refuses an unauthenticated call (HTTP 401); a newly added operation that is not protected fails this check.
9. **Given** an unauthenticated booking request supplies a user identifier in the body, **When** it is submitted, **Then** it is refused (HTTP 401); supplying an identity never counts as proving it.

---

### User Story 3 - Book seats as the signed-in user (Priority: P1)

A signed-in user selects seats and confirms. The booking is stored for the user who signed in. There is no way to pick or send a different user.

**Why this priority**: It ties the booking to a proven identity, which is what makes authentication meaningful, and it replaces the user selector from feature 001.

**Independent Test**: Sign in as Ravi, book seat 3 on Bus A, and verify the stored booking carries Ravi's identifier; attempt the same call while naming Asha in the body and verify it is refused.

**Acceptance Scenarios**:

1. **Given** Asha is signed in and seats 3 and 4 of Bus A are available, **When** she selects both and confirms, **Then** the booking succeeds (HTTP 201), one booking record per seat is stored carrying Asha's user identifier, and the UI shows a success message listing seats 3 and 4.
2. **Given** Ravi is signed in, **When** he views the booking screen, **Then** no user selector is shown; the page shows only that he is signed in as "Ravi".
3. **Given** Ravi is signed in, **When** a direct request registers a booking whose body also contains a user identifier (Ravi's, Asha's, or any other), **Then** it is rejected with a validation error (HTTP 422) and no booking is stored; the booking user can only come from the session.
4. **Given** Asha is signed in, **When** she books a seat already booked by Ravi, **Then** the outcome is the same conflict (HTTP 409) as in feature 001 and no booking is stored.
5. **Given** two users, Asha and Ravi, are signed in at the same time (separate browsers), **When** each books a different seat, **Then** each booking carries its own booker's identifier and neither user ever sees or influences the other's session.
6. **Given** Asha is signed in, **When** all booking rules of feature 001 (1 to 6 distinct seats, seat in range, all-or-nothing, no double-booking under 20 simultaneous attempts) are exercised, **Then** they behave exactly as specified in feature 001, with the user taken from the session instead of the body.

---

### User Story 4 - Sign out and require authentication again (Priority: P2)

A signed-in user can choose "Sign out" at any time. From that moment the application behaves as if they never signed in: buses and booking are unavailable until they authenticate again with the right credentials.

**Why this priority**: It is explicitly requested and completes the session lifecycle, but it only matters once sign-in and protection exist.

**Independent Test**: Sign in, note the session credential used by the browser, sign out, then replay a protected call with that same credential and verify it is refused; press the browser Back button and verify no bus data is shown.

**Acceptance Scenarios**:

1. **Given** Asha is signed in, **When** she selects "Sign out", **Then** the sign-out succeeds (HTTP 204), the UI returns to the sign-in screen, and no bus, seat, or booking data remains on screen.
2. **Given** Asha has just signed out, **When** a request that re-uses her earlier session credential calls any protected operation (list buses, get a bus, book a seat), **Then** it is refused (HTTP 401) and no data is returned or changed; signing out ends the session on the server, not only in the browser.
3. **Given** Asha has signed out, **When** she presses the browser Back button or opens a bus address directly, **Then** the sign-in screen is shown and no previously viewed bus or seat data is displayed.
4. **Given** Asha has signed out, **When** she signs in again with the right credentials, **Then** a new session starts (HTTP 200), the new session works, and the old session credential remains refused.
5. **Given** Asha is signed in on two browsers or in two tabs (two sessions), **When** she signs out on the first, **Then** the first session is refused afterwards, and the second session is unaffected until it is itself signed out or expires.
6. **Given** a sign-out request carries no valid session, **When** it is submitted, **Then** it is refused (HTTP 401), and the UI, whenever it finds that its session is no longer valid, returns to the sign-in screen.
7. **Given** the signed-in UI, **When** it is displayed at any viewport width from 320 px upward, **Then** a "Sign out" control and the name of the signed-in user are visible and keyboard-operable on every screen of the application.
8. **Given** Asha is signed in in one browser tab, **When** she opens the application in a new tab or reopens the browser after closing the tab, **Then** the new tab shows the sign-in screen and no bus or seat data; a sign-in belongs to the tab where it was made.

---

### User Story 5 - Sessions end by themselves (Priority: P2)

A sign-in does not last forever. After a fixed time, the session ends and the user must sign in again, so a forgotten browser or a leaked credential stops working on its own.

**Why this priority**: Required for "short-lived" sessions in the project constitution, but the core allow/deny behaviour works without it.

**Independent Test**: Sign in, advance the clock beyond the session lifetime, and verify a protected call is refused (HTTP 401) and the UI returns to sign-in.

**Acceptance Scenarios**:

1. **Given** Asha signed in 30 minutes and 1 second ago, **When** her session credential is sent to any protected operation, **Then** it is refused (HTTP 401) and no data is returned or changed.
2. **Given** Asha signed in 29 minutes ago, **When** her session credential is sent to a protected operation, **Then** the call is allowed.
3. **Given** Asha's session expires while she is on the seat page, **When** she confirms a booking, **Then** the booking is refused (HTTP 401), nothing is stored, and the UI returns to sign-in with the message "Your session has expired. Please sign in again."
4. **Given** an expired session, **When** the user signs in again with the right credentials, **Then** a fresh session starts and the application works again.

---

### User Story 6 - Repeated wrong guesses are slowed down (Priority: P3)

Someone who keeps entering wrong passwords for a username cannot keep guessing quickly. After a few failures, further attempts for that username are refused for a short while, even if the right password is then entered.

**Why this priority**: Protects the "only the right combination is allowed" promise against guessing, but the feature is usable and correct without it.

**Independent Test**: Submit 5 wrong passwords for `asha`, then the right one, and verify the sixth attempt is refused as throttled; after the wait, verify the right password works.

**Acceptance Scenarios**:

1. **Given** 5 consecutive failed sign-ins for username `asha` within 5 minutes, **When** a sixth attempt arrives (with the right or wrong password), **Then** it is refused (HTTP 429) with the code `too_many_attempts`, the response says when to retry, and no session is created.
2. **Given** `asha` is throttled, **When** 60 seconds have passed since the last failed attempt, **Then** a sign-in with the right password succeeds (HTTP 200).
3. **Given** `asha` is throttled, **When** a visitor signs in as `ravi` with Ravi's right password, **Then** it succeeds; throttling is per username and does not lock out other users.
4. **Given** 4 failed sign-ins for `asha` followed by a successful one, **When** further wrong attempts occur, **Then** the failure count starts again from zero.
5. **Given** repeated failures for a username that does not exist (for example `nobody`), **When** the sixth attempt arrives, **Then** it receives the same throttled outcome (HTTP 429), so throttling does not reveal which usernames exist.

---

### Edge Cases

- The backend or database is unreachable at sign-in: the UI shows "Service unavailable, please try again" and stays on the sign-in screen; no session is created.
- The backend is unreachable while a signed-in user performs an action: the UI keeps the session and shows the existing service-unavailable message; it signs the user out only when the server says the session is invalid (HTTP 401).
- The user presses the sign-in button repeatedly (double click): at most one session is created per submit, and the UI ignores repeat submits while a request is in flight.
- The user opens the application in a second tab while signed in elsewhere: the new tab shows the sign-in screen; signing in there creates a second, independent session, and the first remains valid until it ends.
- The user closes a tab without signing out: the browser forgets the session credential at once; the server-side session is no longer reachable by the user and ends at its expiry.
- The user signs out while a booking request is in flight: if the sign-out is processed first, the booking is refused (HTTP 401) and nothing is stored; if the booking is processed first, it is stored once and the sign-out then proceeds. In neither case is a booking stored without a valid session at processing time.
- A booking request and an expiry occur at the same moment: the decision is made once, at processing time, and is either a complete booking or a refusal with nothing stored (no partial data).
- The browser blocks or clears its own stored data: the UI shows the sign-in screen; no error screen is shown.
- The password contains spaces, accents, symbols, or is exactly 128 characters: it is accepted for comparison without alteration (no trimming or case change); a 129th character is rejected with a validation error (HTTP 422).
- Very small screens (320 px wide): the sign-in screen and the signed-in header (user name and Sign out) remain fully usable without horizontal scrolling.
- Health check operations remain callable without signing in and return no business data.

## Requirements *(mandatory)*

### Functional Requirements

**Mock credentials**

- **FR-001**: Each mock user MUST have a unique username in addition to the existing identifier and name, and MUST have a password known to the mock data loader. No sign-up, password change, profile update, password reset, or user deletion is provided by this feature.
- **FR-002**: The system MUST store only a salted, one-way hash of each password; the plain password MUST NOT be stored, returned by any operation, logged, or placed in evidence files.
- **FR-003**: Loading the mock data MUST (re)create the mock users with their usernames and credentials in a repeatable way, and MUST end all existing sessions, so a reset always returns the system to the same known state.
- **FR-004**: The mock users from feature 001 (at least 3 users, including "Asha" and "Ravi") MUST each be given a username and a password; bookings and buses are unchanged.

**Signing in**

- **FR-005**: The system MUST provide a sign-in operation that accepts exactly a username and a password and, only when the pair matches one mock user exactly, starts a session for that user and returns the user's identifier, display name, and the session credential.
- **FR-006**: The username and password MUST match exactly (case-sensitive, no trimming). A correct password for a different user MUST NOT succeed.
- **FR-007**: Any failed sign-in (unknown username, wrong password, wrong user/password pair) MUST return the same status (HTTP 401), the same error code (`invalid_credentials`), the same message, and the same response shape, and MUST take a comparable amount of time, so existing usernames cannot be discovered.
- **FR-008**: The sign-in request MUST be validated: username 1 to 50 characters, password 1 to 128 characters, no other fields; violations MUST be rejected (HTTP 422) before any credential check.
- **FR-009**: Each successful sign-in MUST start a new, independent session with a defined start and expiry; one user MAY hold several sessions at once.
- **FR-010**: A session MUST end 30 minutes after it starts, with no extension on use; after that, its credential MUST be refused everywhere.
- **FR-011**: The system MUST record each sign-in success, sign-in failure, throttled attempt, and sign-out with a timestamp and the username attempted (never the password), for review.

**Protecting the API**

- **FR-012**: Every operation of the API other than sign-in and the two health checks MUST require a valid, unexpired, not-signed-out session; this includes listing buses, getting a bus with seats, and registering a booking.
- **FR-013**: A call without a valid session MUST be refused with HTTP 401, the common error shape, the code `unauthenticated`, and a generic message that does not reveal why the session was not accepted; it MUST NOT return or change any data.
- **FR-014**: The session check MUST be performed on the server for every call, before the request body or parameters are processed, and MUST NOT depend on anything the client states about itself (user name, user identifier, role, or "signed in" flags).
- **FR-015**: A session credential that is forged, altered, issued for another system, empty, malformed, expired, belongs to a user that no longer exists, or belongs to a signed-out session MUST be refused (HTTP 401).
- **FR-016**: The system MUST NOT provide any sign-in shortcut, default credential, debug override, environment switch, or alternate route that grants access without a matching username and password.
- **FR-017**: Operations added in the future MUST be protected by default; the system MUST include an automated check that fails if any operation other than the three public ones accepts an unauthenticated call.
- **FR-018**: The 001 operation that lists users MUST be removed (calls return 404 whether signed in or not), and no operation or screen may reveal the names, usernames, or identifiers of users other than the signed-in user. The user selector of feature 001 is retired. No response may ever include passwords or password hashes.

**Booking as the signed-in user**

- **FR-019**: The booking operation MUST take the booking user only from the session. A booking request body MUST contain only the bus identifier and the seat numbers; a request that also contains a user identifier (or any other unknown field) MUST be rejected with HTTP 422 and store nothing.
- **FR-020**: All other booking rules of feature 001 (FR-010 to FR-017 there, including 1 to 6 distinct seats, validation, UTC booking datetime set by the system, all-or-nothing, conflict handling, error shape) MUST continue to apply unchanged, except that "user identifier does not exist" can no longer arise from the request.
- **FR-021**: The system MUST NOT allow a user to create, view, or change bookings on behalf of another user through this feature.

**Signing out and session end**

- **FR-022**: The system MUST provide a sign-out operation that ends the caller's current session on the server, returns HTTP 204, and from then on causes that session's credential to be refused everywhere (HTTP 401).
- **FR-023**: Signing out MUST end only the current session; other sessions of the same user remain valid until they end.
- **FR-024**: A sign-out call without a valid session MUST be refused (HTTP 401).
- **FR-025**: After sign-out or expiry, the user MUST authenticate again with the right username and password before any bus, seat, or booking operation is possible again.

**Guessing protection**

- **FR-026**: After 5 consecutive failed sign-in attempts for the same username within 5 minutes, the system MUST refuse all further sign-in attempts for that username (HTTP 429, code `too_many_attempts`, with the time to wait) until 60 seconds have passed since the last failed attempt; the right password MUST NOT bypass this wait.
- **FR-027**: The throttle MUST apply equally to usernames that do not exist, MUST NOT affect other usernames, and MUST reset to zero on a successful sign-in.

**User interface**

- **FR-028**: When no valid session exists, the UI MUST show only the sign-in screen for every address of the application, and MUST NOT request or display any bus, seat, user, or booking data.
- **FR-029**: The sign-in screen MUST provide labelled username and password fields (password masked), a submit action that is disabled while a request is in flight, and a readable error message for each failure kind: invalid credentials, too many attempts (with the wait time), validation, and service unavailable.
- **FR-030**: After a successful sign-in, the UI MUST show the bus list, the signed-in user's name, and a "Sign out" control on every screen; the booking screen MUST NOT show a user selector.
- **FR-031**: Choosing "Sign out" MUST call the sign-out operation, discard every piece of session information held by that tab of the browser, clear all displayed bus, seat, and booking data, and show the sign-in screen, even if the sign-out call itself fails (in which case the server-side session is still treated as ended by expiry).
- **FR-032**: Whenever any request is refused with HTTP 401 for lack of a valid session, the UI MUST discard its session information and return to the sign-in screen with a message ("Your session has expired. Please sign in again." for an existing session); it MUST NOT show this as a generic failure.
- **FR-033**: A page reload in the same tab while the session is still valid MUST keep the user signed in; a page reload after sign-out or expiry, and any new tab or reopened browser, MUST show the sign-in screen. A sign-in MUST belong to the single tab where it was made and MUST NOT be shared with other tabs or survive closing the tab.
- **FR-034**: The sign-in screen and the signed-in header MUST meet the project's loading, error, responsiveness, and accessibility rules (no horizontal scroll from 320 px, keyboard operation, text labels).

**Changes to feature 001**

- **FR-035**: Feature 001 requirements that this feature supersedes are: the user selector and the user list (001 User Story 4, FR-009, FR-020 in part), the user identifier in the booking request (001 FR-010 in part; 001 User Story 2 scenarios 1 and 5), and the "no sign-in" assumption. All other 001 requirements stay in force. The tests of feature 001 that depended on the superseded behaviour are updated through the feature 002 specification, plan, and tasks, and are not removed or weakened for the unchanged behaviour.

### Non-Functional Requirements

- **NFR-001 (Security: bypass resistance)**: Across an automated suite that attempts at least 10 distinct bypass techniques (no credential, empty credential, malformed credential, altered credential, credential of a signed-out session, credential of an expired session, credential for a deleted user, client-supplied user identifier or "signed in" flag, wrong HTTP method or extra path segments on protected addresses, request with a valid body but no session), 100% MUST be refused (HTTP 401 for every protected address including a wrong method, 404 for an address that matches no route) with zero data returned and zero data changed.
- **NFR-002 (Security: credentials)**: No password, password hash, or session signing secret appears in source code, committed seed data, tests, fixtures, logs, error responses, evidence files, or the browser address bar; mock passwords and the session signing secret are supplied only through the environment configuration, in line with the project constitution; the example environment file lists names only.
- **NFR-003 (Security: uniform failure)**: For 1,000 failed sign-ins mixing unknown usernames and wrong passwords, 100% MUST return identical status, error code, message, and body shape, and the 95th-percentile response times of the two groups MUST differ by no more than 50 ms.
- **NFR-004 (Security: transport and storage)**: Session information held by the browser MUST be removed at sign-out, at expiry, and when the tab is closed, and MUST NOT be placed in page addresses.
- **NFR-005 (Performance: sign-in)**: Sign-in MUST complete in under 500 ms at the 95th percentile on a local development machine, including the password check.
- **NFR-006 (Performance: protection overhead)**: The session check MUST add no more than 50 ms at the 95th percentile to any protected operation, so the targets of feature 001 (seat list under 300 ms and booking under 500 ms at the 95th percentile with 1,000 stored bookings) still hold with authentication in place.
- **NFR-007 (Consistency)**: A sign-out MUST take effect for all later calls immediately: 0 of 100 protected calls started after the sign-out response was received may succeed with the ended session's credential.
- **NFR-008 (Reliability)**: A refused authentication or sign-in attempt MUST leave the bookings and buses tables unchanged; the only data that may change is sessions and sign-in records.
- **NFR-009 (Stateless scaling)**: The server MUST keep no sign-in state in its own memory; session state MUST live in the database so that any number of server instances give the same answer to the same credential.
- **NFR-010 (Usability)**: A user can go from the sign-in screen to the bus list in 3 or fewer interactions (type username, type password, submit), and from the bus list to a confirmed booking of one seat in 3 or fewer interactions (choose bus, select seat, confirm), one fewer than in feature 001.
- **NFR-011 (Responsiveness and accessibility)**: The sign-in screen and signed-in header are usable without horizontal scrolling at 320 px, 768 px, and 1280 px; all controls are keyboard-operable; each field has a text label; error messages are announced to assistive technology.
- **NFR-012 (Auditability)**: 100% of sign-in successes, failures, throttled attempts, and sign-outs produce one record each, with timestamp and username attempted and no password.
- **NFR-013 (Maintainability and quality)**: Every functional requirement, non-functional requirement, and acceptance scenario above has at least one automated test written first and observed failing; backend line coverage stays at or above 85% (branch at or above 80%) and frontend line coverage at or above 80%; lint, type, security, dependency-audit, and secret-scan gates report zero violations, per the project constitution.
- **NFR-014 (Reproducibility)**: From a fresh checkout with the environment file in place, one documented command sequence starts the database, loads the mock users with credentials, and runs the application; the README states how to find the mock usernames and where the mock passwords are configured.

### Key Entities *(include if feature involves data)*

- **User** (extended from feature 001): A mock person who can sign in. Attributes: identifier, name, username (unique), password hash (never exposed). Sign-up, update, and delete are out of scope. Adding the username and password hash is justified by the need to prove identity; no other user attribute is added.
- **Session**: A record that a user is currently signed in. Attributes: session identifier, user, start time, expiry time, ended time (empty while the session is open). A session is valid only while it has not expired and has not ended. It is a new table, justified because sign-out must end a session on the server and stateless scaling forbids holding sessions in server memory.
- **Sign-in attempt record**: One entry per sign-in success, failure, throttled attempt, or sign-out. Attributes: timestamp, username attempted, outcome. It also provides the failure count used for throttling. Never holds a password.
- **Booking** (changed from feature 001): the user on a booking is always the session's user; there is no way to supply a different one.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of attempts with a correct username and password pair succeed, and 100% of attempts with any other pair (wrong password, unknown username, another user's password, altered case or spacing, injection-style text) fail with an identical, non-revealing message.
- **SC-002**: 0 of the bypass attempts in the automated suite (at least 10 techniques, each applied to every protected operation) obtain or change any data.
- **SC-003**: 100% of operations other than sign-in and health checks refuse an unauthenticated call, verified by an automated check over the whole API.
- **SC-004**: After sign-out, 0 of 100 later calls using the old credential succeed, and the browser Back button shows no bus or seat data.
- **SC-005**: 100% of bookings stored through the UI or the API carry the identifier of the user who signed in, and 0 bookings carry a client-supplied identity.
- **SC-006**: A user can sign in and have the bus list showing within 3 interactions and 2 seconds on a local environment, and can complete a one-seat booking in 3 interactions after reaching the bus list.
- **SC-007**: After 5 consecutive wrong passwords for one username, 0 further attempts for that username succeed during the 60-second wait, and 0 other usernames are affected.
- **SC-008**: Sessions older than 30 minutes are refused in 100% of tests.
- **SC-009**: Sign-in, sign-out, and the signed-in header are fully usable at 320 px, 768 px, and 1280 px without horizontal scrolling.
- **SC-010**: Every functional and non-functional requirement and acceptance scenario is covered by at least one automated test, the booking and seat-viewing behaviour of feature 001 is unchanged apart from superseded items, and all automated quality gates pass.

## Assumptions

- Authentication means proving identity with a mock username and password; roles, permissions, and per-user data rules beyond "the booking belongs to the signed-in user" are out of scope. Every signed-in user may view all buses and book any available seat, as in feature 001.
- Sign-up, password change, reset, profile update, user deletion, "remember me", multi-factor sign-in, third-party sign-in, and email are out of scope.
- "User id" in the request is treated as the username, a short text login name distinct from the numeric user identifier; users enter the username, never the numeric identifier. Usernames are lower-case text such as `asha` and `ravi`.
- Mock passwords are demo values only. To satisfy the project constitution (no secrets in source, tests, fixtures, or evidence), their plain values are supplied through the environment configuration (not committed) and read by the mock data loader and by the tests; only their salted hashes reach the database. The planning phase decides the exact variable names.
- Session length is a fixed 30 minutes from sign-in with no extension on use; throttling uses 5 failures in 5 minutes and a 60-second wait, applied per username. Someone who knows a username can therefore keep that user waiting for short periods; this is accepted for the mock scenario. These are reasonable defaults and can be changed by a later specification change.
- The three public operations are sign-in and the two health checks; the health checks return no business data.
- The standard project rules still apply: consistent error shape, input validation at every boundary, no leaked internals, versioned API prefix, stateless server, versioned schema changes (new user columns and the session and sign-in record tables), and harness-driven verification.
- Existing feature 001 data (buses, bookings) is kept; user rows gain usernames and credentials through a versioned schema change and the repeatable mock data load.
- Feature 001 has been closed (ACCEPT recorded). This feature is built as a new specification under the current constitution (v1.4.1); superseded 001 behaviour is changed only through this specification, plan, and tasks.
- Browsers used for checking are current desktop and mobile browsers; keeping the session in the tab until sign-out, expiry, or closing the tab is acceptable for this mock scenario.
