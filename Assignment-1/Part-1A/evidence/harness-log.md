# Harness Log: 001-seat-booking (Bus Seat Booking)

Chronological record required by constitution v1.3.1 (Principles XII and XIII).

## Approval

Implementation MUST NOT start until a human replaces `PENDING` below with `APPROVED`, their name, and the
date. The coding agent MUST NOT write this decision.

| Artifact | Last modified | Decision | Approved by | Date |
|----------|---------------|----------|-------------|------|
| `specs/001-seat-booking/spec.md` | 2026-11-02 | APPROVED | Siddharth | 2026-11-02 |
| `specs/001-seat-booking/plan.md` | 2026-11-02 | APPROVED | Siddharth | 2026-11-02 |
| `specs/001-seat-booking/tasks.md` | 2026-11-02 | APPROVED | Siddharth | 2026-11-02 |
| `.specify/memory/constitution.md` (v1.3.1) | 2026-11-02 | APPROVED | Siddharth | 2026-11-02 |

## Initial generation and context

**Snapshot**: git tag `initial-generation` on commit `0f02bdff5c2e5a3daa4ae2d164192f16c108a8a5` (`0f02bdf`, "feat: polish, performance and documentation"), created on 2026-11-03 before any recorded harness run. The tag contains tasks T001-T127 as implemented by the coding agent (Spec Kit `/speckit-implement`), phase by phase with a stop and report at every checkpoint. A copy of `src/`, `tests/`, `.harness/`, and the approved `spec.md`, `plan.md`, `tasks.md` (without `node_modules`, `dist`, and caches) is in `evidence/initial-generation/`.

**Context given to the agent**:

- `.specify/memory/constitution.md` v1.3.1, `specs/001-seat-booking/spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`, and `tasks.md`, all approved by a human in the Approval table above (dated 2026-11-02).
- The guardrails in `tasks.md`: tests first and seen failing, harness built before application code, no weakening of tests or thresholds, protected files (`.harness/`, `ruff.toml`, `mypy.ini`, `eslint.config.js`, `tsconfig.json`), no changes to `.env` or to other databases on the container.
- Changes after the approval date: Chrome Canary replaced Edge for Playwright (Edge remote debugging is blocked by managed policy), and task T135 (DB-tooling tests) plus a "DB tooling" row in `plan.md` were added on 2026-11-03 after backend branch coverage measured 61.1% against the 80% minimum. The Approval table dates predate these two changes.
- Phase 7 added two files not listed in `tasks.md` to close traceability gaps: `tests/backend/contract/test_input_safety.py` and `tests/backend/unit/test_bundle_size_check.py`.

**Development gate results at the snapshot** (not evidence; run by hand at the T127 checkpoint): integrity, lint, security, test, build, and e2e all passed; backend 270 tests with line 98.3% and branch 88.9% coverage, frontend 74 tests with line 91.5%, initial JS 80.3 KB gzipped, 14 end-to-end specs.

**Commits in the tag**:

```text
0f02bdf feat: polish, performance and documentation
b63c71d test: acceptance traceability and two gap-closing test files (T126)
143b8ec docs: README, quickstart uv flow, keep existing container (T123-T125)
03fa813 feat: scripts/dev.sh single start command (T122)
4f4f4c9 test: scripts/dev.sh branch tests written first (T122)
c9d24fa test: responsive, usability, keyboard and architecture tests (T119-T121)
16d21b8 test: performance and OpenAPI contract tests (T117, T118)
65132e3 test: DB tooling tests lift backend branch coverage to 88.9% (T135)
7819d28 docs: add T135 DB-tooling tests task
81b2199 feat(us3): conflict protection and persistence
2936bff feat(us3): conflict protection (browser checks blocked; T110, T115, T116 open)
c03aca7 feat(us2): book seats
5f757a4 test(us2): booking tests written first (T091-T096)
90df6d2 feat(us4): choose the booking user
ce6a55d test(us4): user list and selector tests written first (T081-T083)
753ebdf feat(us1): view buses and seats
feff7b0 test(us1): bus and seat view tests written first (T064-T068)
8e12219 feat: application foundation
e234e99 test: foundation tests written first (T031-T038)
0e876d2 chore: deterministic harness (gates, thresholds, integrity checksums)
73ff5d1 chore: project skeleton and tool configuration
dd29c26 chore: added basic setup after first approval, and first phase of env and skeleton setup
0f7696f docs: approved constitution v1.3.1, spec, plan, tasks
9daeb6e chore(docs): ratify constitution v1.0.0 (bus booking platform, SDD harness gates)
```

## Failure and repair log

No repair was needed. The first recorded run (`evidence/harness-results/20261103T091218Z`, row dated 2026-11-03T09:13:31Z in the run table) passed every gate on the first attempt: integrity, lint, security, test, build, and e2e all PASS with 0 failed tests. No application code, test, threshold, or harness script was changed in response to the run, and no failure was created artificially.

## Quickstart validation

Run on 2026-11-03 against the stack started by `scripts/dev.sh` (existing `azure-sql-edge` container reused, `bus_db` freshly seeded: "seeded 3 buses, 3 users, 0 bookings"). Scenarios 1-5 used `curl` against http://localhost:8000; scenarios 6-7 drove http://localhost:5173 in Chrome Canary with a throwaway Playwright script (not part of the suite). Afterwards `scripts/dev.sh` was stopped with SIGINT; both processes ended and the database container kept running.

| # | Scenario | Expected | Observed | Result |
|---|----------|----------|----------|--------|
| 1 | List buses | 3 buses, Bus A with 20 seats | 3 buses: Bus A 20, Bus B 30, Bus C 40 | PASS |
| 2 | View seats of bus 1 | 20 seats, all available | 20 seats, statuses `{available}` | PASS |
| 3 | Book seats 3 and 4 | 201, two bookings with one `booked_at` | 201; ids 1 and 2, both `booked_at` 2026-11-03T09:14:22.931500Z | PASS |
| 4 | Reflected, then repeat | seats 3, 4 booked; repeat gives 409 `seat_unavailable` | booked seats `[3, 4]`; repeat gave 409 `seat_unavailable` | PASS |
| 5 | Validation | empty, duplicate, 7 seats, seat 0: 422; seat 21: 400; bus 99, user 99: 404; body `{"error": {"code", "message"}}` | empty 422, duplicate 422, 7 seats 422, seat 0 422 (all `validation_error`); seat 21 400 `invalid_seat`; bus 99 404 `bus_not_found`; user 99 404 `user_not_found`; bookings unchanged (`[3, 4]`) | PASS |
| 6 | UI booking of seats 5, 6 as Asha, then reload | success message listing 5 and 6; seats booked; still booked after reload | message "Booked seats 5, 6."; both seats booked and disabled; after reload still booked and disabled | PASS |
| 7 | Conflict in UI (stale tab) | UI says seat no longer available and refreshes | seat 7 booked through the API (201) while a stale tab had it selected as Ravi; Confirm showed the alert "Seat no longer available. The seat list has been refreshed."; seat 7 then shown booked and disabled; API log shows 201 then 409 | PASS |
| 8 | Reset with `scripts/db-init.sh` | seeded state | "seeded 3 buses, 3 users, 0 bookings"; no booked seats on bus 1; 3 buses | PASS |

Scenario 7 booked seat 7 through a `fetch` call to the same endpoint instead of the `curl` command; the request is identical.

## Convergence results

`/speckit-converge` was run on 2026-11-03 after the first recorded harness run (`evidence/harness-results/20261103T091218Z`, all gates PASS). No extension hooks are registered (`.specify/extensions.yml` does not exist). The command only appended `## Phase 9: Convergence` (T136-T141) to `tasks.md`; no spec, plan, or application file was changed by it.

**Checked**: 24 functional requirements, 11 non-functional requirements, 7 success criteria, 17 acceptance scenarios and 7 edge cases (traced to named tests in the Acceptance traceability section below); the plan's key decisions and every planned file; all 13 constitution principles.

| ID | Gap type | Severity | Source | Evidence | Remaining work (task) |
|----|----------|----------|--------|----------|-----------------------|
| F1 | contradicts | CRITICAL | Constitution III | `Any` without a justification comment in `src/backend/app/db/seed.py` (lines 3, 10, 15) and `src/backend/app/api/schemas/common.py` (lines 2, 46); no gate checks this (ruff rules exclude `ANN401`, `mypy --strict` allows explicit `Any`) | T136 (test), T137 (fix) |
| F2 | contradicts | CRITICAL | Constitution III | `Any` without justification in six backend test files, and `# type: ignore[no-untyped-call]` without justification in `tests/backend/unit/test_db_tooling.py` (line 53) | T138 |
| F3 | partial | MEDIUM | Constitution V | T117, T119, T120, T121, and T135 were written after the code they cover (the code was built in earlier phases); each test was shown able to fail by mutation, as recorded in the commit messages, but was not observed failing before the code existed | T139 |
| F4 | partial | LOW | FR-017, `contracts/openapi.yaml` | Unknown routes and wrong methods return the shared error shape with codes `not_found` and `method_not_allowed`, which are not in the contract's code enum; the contract test compares property names, not enum values | T140 (needs user approval) |
| F5 | unrequested | LOW | plan.md, tasks.md | Files and options not named in the plan: `tests/backend/unit/{harness_loader,layer_scan}.py`, `.harness/check_coverage.py`, `scripts/e2e-reset.sh`, `scripts/e2e-backend.sh`, `src/frontend/e2e/{support,global-setup}.ts`, `@types/node`, `scripts/dev.sh --db-only`, `contract/test_input_safety.py`, `unit/test_bundle_size_check.py`, `unit/test_dev_script.py`, the `HealthOut` schema | no new task: T133 already requires a note on every unplanned helper file |

**Findings by gap type**: contradicts 2, partial 2, unrequested 1, missing 0. **By severity**: CRITICAL 2, MEDIUM 1, LOW 2. Tasks appended: 6 (T136-T141; T141 re-runs the harness unchanged after the fixes). Next: complete T136-T141, then T133.

## Acceptance traceability

Filled by T126 against `specs/001-seat-booking/spec.md`. Backend tests are `tests/backend/<folder>/<file>::<test>`; frontend unit tests are `src/frontend/tests/<file>`; end-to-end specs are `src/frontend/e2e/<file>`. "BE" means `tests/backend`.

### Functional requirements

| ID | Named tests |
|----|-------------|
| FR-001 | BE integration/test_schema_and_seed.py::test_schema_has_exactly_the_application_tables; BE unit/test_settings.py::test_database_url_targets_the_requested_database |
| FR-002 | BE integration/test_schema_and_seed.py::test_total_seats_outside_1_to_60_is_rejected, ::test_duplicate_and_blank_names_are_rejected; BE unit/test_bus_service.py::test_seats_are_numbered_one_to_total_in_order |
| FR-003 | BE integration/test_schema_and_seed.py::test_seed_yields_the_documented_mock_data; BE contract/test_users.py::test_list_returns_the_seeded_users_in_id_order |
| FR-004 | BE contract/test_bookings_create.py::test_one_row_per_seat_is_stored_with_the_server_time; BE integration/test_schema_and_seed.py::test_seat_number_below_1_is_rejected |
| FR-005 | BE integration/test_schema_and_seed.py::test_seed_yields_the_documented_mock_data, ::test_seed_is_idempotent_and_resets_bookings; BE integration/test_db_tooling.py::test_seed_main_reseeds_the_given_database_and_prints_only_counts |
| FR-006 | BE integration/test_schema_and_seed.py::test_a_second_booking_for_the_same_bus_and_seat_is_rejected, ::test_same_seat_on_another_bus_is_allowed |
| FR-007 | BE contract/test_buses.py::test_list_returns_the_three_seeded_buses, ::test_list_honours_the_requested_page_size, ::test_invalid_paging_is_rejected |
| FR-008 | BE contract/test_buses.py::test_detail_lists_every_seat_as_available_when_nothing_is_booked, ::test_detail_marks_only_the_booked_seat; BE unit/test_bus_service.py::test_booked_numbers_map_to_booked_and_the_rest_to_available |
| FR-009 | BE contract/test_users.py (all four tests); BE unit/test_user_service.py |
| FR-010 | BE contract/test_bookings_create.py::test_booking_two_seats_returns_201_with_one_shared_utc_timestamp, ::test_six_seats_are_accepted |
| FR-011 | BE contract/test_bookings_create.py::test_invalid_seat_lists_are_rejected_with_422_and_store_nothing, ::test_invalid_bodies_are_rejected_with_422_and_store_nothing, ::test_a_seat_beyond_the_bus_is_rejected_with_400, ::test_unknown_bus_is_rejected_with_404, ::test_unknown_user_is_rejected_with_404; BE unit/test_booking_schema.py; BE unit/test_booking_service.py::test_the_bus_is_checked_before_the_user |
| FR-012 | BE contract/test_bookings_create.py::test_booking_two_seats_returns_201_with_one_shared_utc_timestamp, ::test_invalid_bodies_are_rejected_with_422_and_store_nothing (a client-supplied `booked_at` is refused); BE unit/test_booking_service.py::test_books_every_seat_with_one_timestamp_from_the_clock; BE unit/test_db_tooling.py::test_utc_datetime_stores_an_aware_datetime_as_naive_utc, ::test_utc_datetime_returns_a_utc_aware_datetime_on_read |
| FR-013 | BE contract/test_bookings_create.py::test_one_row_per_seat_is_stored_with_the_server_time |
| FR-014 | BE integration/test_booking_conflicts.py::test_one_taken_seat_stores_none_of_the_requested_seats, ::test_every_kind_of_rejected_request_leaves_the_table_identical |
| FR-015 | BE integration/test_booking_conflicts.py::test_second_booking_of_a_seat_returns_409_and_changes_nothing, ::test_twenty_simultaneous_requests_book_one_seat_exactly_once |
| FR-016 | BE contract/test_bookings_create.py::test_booking_two_seats_returns_201_with_one_shared_utc_timestamp |
| FR-017 | BE unit/test_error_handlers.py (all four tests); BE contract/test_conflict_response.py; BE contract/test_no_secret_leak.py; BE contract/test_health.py::test_readiness_returns_503_without_leaking_details_when_the_database_fails; BE contract/test_input_safety.py::test_error_bodies_do_not_echo_the_submitted_text |
| FR-018 | tests/components/SeatGrid.test.tsx (renders one control per seat..., disables booked seats and labels them with text, not colour alone); tests/components/BusList.test.tsx; tests/pages/BusSeatsPage.test.tsx "lists every seat with booked seats marked" |
| FR-019 | tests/hooks/useSeatSelection.test.ts (toggles a seat on and off, cannot select a booked seat, ignores a seventh seat and reports the limit); tests/pages/BusSeatsPage.booking.test.tsx "cannot select a seventh seat"; tests/pages/BusSeatsPage.keyboard.test.tsx "shows the 6-seat limit message..." |
| FR-020 | tests/components/UserSelect.test.tsx; tests/components/BookingBar.test.tsx (enabled/disabled cases); tests/pages/BusSeatsPage.booking.test.tsx "disables Confirm without a user or without seats" |
| FR-021 | tests/pages/BusSeatsPage.booking.test.tsx "sends the booking, shows progress, then success, and re-reads the seats" |
| FR-022 | tests/api/client.test.ts (error mapping); tests/pages/BusSeatsPage.booking.test.tsx "on a conflict shows an alert...", "on a 503 response / a network failure shows Service unavailable...", "on a 400/422 response shows Invalid request" |
| FR-023 | e2e/booking-persistence.spec.ts "seats booked through the UI are still booked after a reload" |
| FR-024 | tests/pages/BusListPage.test.tsx (loading, empty, error with Retry); tests/pages/BusSeatsPage.test.tsx "shows a loading state...", "shows an error with Retry and no partial seat list" |

### Non-functional requirements

| ID | Named tests or checks |
|----|-----------------------|
| NFR-001 | BE integration/test_performance.py::test_bus_detail_p95_is_under_the_read_limit (limit from `READ_P95_MS`) |
| NFR-002 | BE integration/test_performance.py::test_six_seat_booking_p95_is_under_the_write_limit (limit from `WRITE_P95_MS`) |
| NFR-003 | BE integration/test_booking_conflicts.py::test_twenty_simultaneous_requests_book_one_seat_exactly_once |
| NFR-004 | BE contract/test_no_secret_leak.py; BE unit/test_settings.py::test_password_never_appears_in_repr_str_or_database_url_text; BE contract/test_input_safety.py (injection text in identifiers, seats, and paths); BE unit/test_db_tooling.py::test_validated_name_rejects_anything_else; security gate (`bandit`, `pip-audit`, `npm audit`, `gitleaks`) |
| NFR-005 | BE integration/test_booking_conflicts.py::test_every_kind_of_rejected_request_leaves_the_table_identical; BE integration/test_db_tooling.py::test_unit_of_work_rolls_back_and_reraises_when_the_block_fails, ::test_get_session_rolls_back_when_the_request_fails |
| NFR-006 | e2e/responsive.spec.ts (bus list, seat page, and a booking at 320, 768, 1280 px) |
| NFR-007 | BE unit/test_bundle_size_check.py (the checker used by the build gate fails above the limit); build gate `.harness/build.sh` (200 KB gzipped budget from `BUNDLE_MAX_KB_GZIP`); e2e/usability.spec.ts "the bus list is visible within 2 seconds of opening the application" |
| NFR-008 | e2e/usability.spec.ts "one seat is booked in at most 5 interactions and under 30 seconds" |
| NFR-009 | tests/components/SeatGrid.test.tsx (text label and keyboard reachability); tests/pages/BusSeatsPage.keyboard.test.tsx (Tab, Space, Enter, Tab to Confirm) |
| NFR-010 | test gate `.harness/test.sh` (backend line 85%, backend branch 80%, frontend line 80%, no skipped tests); lint gate; security gate; BE unit/test_architecture.py; BE unit/test_check_function_length.py; tests/architecture.test.ts |
| NFR-011 | BE unit/test_dev_script.py (database branches of `scripts/dev.sh`); `scripts/dev.sh` and README.md document the single command |

### Success criteria

| ID | Named tests or checks |
|----|-----------------------|
| SC-001 | e2e/usability.spec.ts "the seat list is visible within 2 seconds of choosing a bus" |
| SC-002 | e2e/usability.spec.ts "one seat is booked in at most 5 interactions and under 30 seconds" |
| SC-003 | e2e/booking-persistence.spec.ts "seats booked through the UI are still booked after a reload"; BE contract/test_buses.py::test_detail_marks_only_the_booked_seat |
| SC-004 | BE integration/test_booking_conflicts.py::test_twenty_simultaneous_requests_book_one_seat_exactly_once |
| SC-005 | BE contract/test_bookings_create.py (invalid seat lists, bodies, seat beyond the bus, unknown bus, unknown user); BE integration/test_booking_conflicts.py::test_every_kind_of_rejected_request_leaves_the_table_identical |
| SC-006 | e2e/responsive.spec.ts |
| SC-007 | this table; test gate `.harness/test.sh` and the other gates run by `.harness/run.sh` |

### Acceptance scenarios

| Scenario | Named tests |
|----------|-------------|
| US1.1 | BE contract/test_buses.py::test_detail_lists_every_seat_as_available_when_nothing_is_booked |
| US1.2 | BE contract/test_buses.py::test_detail_marks_only_the_booked_seat; tests/pages/BusSeatsPage.test.tsx "lists every seat with booked seats marked" |
| US1.3 | BE contract/test_buses.py::test_list_returns_the_three_seeded_buses; tests/pages/BusListPage.test.tsx "lists every bus with its seat count" |
| US1.4 | BE contract/test_buses.py::test_unknown_bus_returns_404; tests/pages/BusSeatsPage.test.tsx "shows a readable message when the bus does not exist" |
| US2.1 | BE contract/test_bookings_create.py::test_booking_two_seats_returns_201_with_one_shared_utc_timestamp, ::test_one_row_per_seat_is_stored_with_the_server_time; tests/pages/BusSeatsPage.booking.test.tsx "sends the booking, shows progress, then success, and re-reads the seats" |
| US2.2 | tests/components/BookingBar.test.tsx "is disabled with no seats selected"; BE contract/test_bookings_create.py::test_invalid_seat_lists_are_rejected_with_422_and_store_nothing (empty list) |
| US2.3 | BE contract/test_bookings_create.py::test_invalid_seat_lists_are_rejected_with_422_and_store_nothing (duplicate seat) |
| US2.4 | BE contract/test_bookings_create.py::test_a_seat_beyond_the_bus_is_rejected_with_400, ::test_invalid_seat_lists_are_rejected_with_422_and_store_nothing (seat 0 and negative) |
| US2.5 | BE contract/test_bookings_create.py::test_unknown_bus_is_rejected_with_404, ::test_unknown_user_is_rejected_with_404 |
| US2.6 | BE contract/test_bookings_create.py::test_invalid_seat_lists_are_rejected_with_422_and_store_nothing (seven seats) |
| US3.1 | e2e/booking-persistence.spec.ts "seats booked through the UI are still booked after a reload" |
| US3.2 | BE integration/test_booking_conflicts.py::test_second_booking_of_a_seat_returns_409_and_changes_nothing; tests/pages/BusSeatsPage.booking.test.tsx "on a conflict shows an alert, refreshes the seats, and drops the taken seat" |
| US3.3 | BE integration/test_booking_conflicts.py::test_one_taken_seat_stores_none_of_the_requested_seats |
| US3.4 | BE integration/test_booking_conflicts.py::test_twenty_simultaneous_requests_book_one_seat_exactly_once |
| US3.5 | BE integration/test_booking_conflicts.py::test_the_same_seat_number_on_another_bus_is_still_bookable; BE contract/test_buses.py::test_bookings_on_one_bus_do_not_affect_another |
| US4.1 | tests/components/UserSelect.test.tsx "is a labelled select with a placeholder and every user"; tests/pages/BusSeatsPage.test.tsx "lists the users in a selector once the seats are shown"; tests/components/BookingBar.test.tsx "is disabled without a user and hints to choose one" |
| US4.2 | tests/pages/BusSeatsPage.booking.test.tsx "sends the booking..." (Ravi's id 2 is sent); BE contract/test_bookings_create.py::test_booking_two_seats_returns_201_with_one_shared_utc_timestamp (stored `user_id`) |

### Edge cases

| Edge case | Named tests |
|-----------|-------------|
| Backend unreachable while loading | tests/pages/BusSeatsPage.test.tsx "shows an error with Retry and no partial seat list"; tests/pages/BusListPage.test.tsx "shows an error with Retry, and Retry loads the buses" |
| Backend unreachable while booking | tests/pages/BusSeatsPage.booking.test.tsx "on a 503 response / a network failure shows Service unavailable and keeps the selection" |
| Seat taken between view and confirm | tests/pages/BusSeatsPage.booking.test.tsx "on a conflict shows an alert, refreshes the seats, and drops the taken seat" |
| Reload before confirming | tests/pages/BusSeatsPage.booking.test.tsx "discards an unconfirmed selection when the page is reloaded"; e2e/booking-persistence.spec.ts "an unconfirmed selection is discarded on reload and nothing is stored" |
| Double click on Confirm | tests/pages/BusSeatsPage.booking.test.tsx "sends only one request when Confirm is clicked twice" |
| Malformed or oversized identifiers | BE contract/test_buses.py::test_malformed_or_oversized_bus_id_is_rejected_with_422; BE unit/test_booking_schema.py::test_invalid_ids_are_rejected; tests/pages/BusSeatsPage.test.tsx (ids "abc", "0", "99999999999999999999") |
| 320 px screens | e2e/responsive.spec.ts |

Gaps found while tracing and closed with new tests: NFR-004 (injection text) by `contract/test_input_safety.py`, and NFR-007 (bundle budget checker) by `unit/test_bundle_size_check.py`. No criterion was reduced.

## Final decision

_Recorded by a human only (T134): ACCEPT or REJECT, known limitations (T133 drafts them), and justification. The agent MUST NOT write the decision._

## Harness run table

Rows are appended by `.harness/run.sh`; do not edit by hand.

| Timestamp | Integrity | Lint | Security | Tests | Build | E2E | Result | Evidence |
|-----------|-----------|------|----------|-------|-------|-----|--------|----------|
| 2026-11-03T09:13:31Z | PASS | PASS | PASS | PASS | PASS | PASS | PASS | evidence/harness-results/20261103T091218Z |
