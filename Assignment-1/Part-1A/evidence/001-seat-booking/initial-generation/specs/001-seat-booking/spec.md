# Feature Specification: Bus Seat Booking

**Feature Branch**: `001-seat-booking`

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "First feature: a simple booking on a given bus against a given seat by a given user. A booking holds booking datetime, bus identifier, user identifier. Bus, user and booking information sit in three temporary tables (mock data) inside bus_db. The database holds the seat details for a bus; the API manages fetching bus details and registering a bus booking; the UI shows a simple list of all seats and lets the user select and book 1 or more seats, which sends the appropriate request, is reflected in the database, and shows the seats as booked when the seat list is viewed again."

## Clarifications

### Session 2026-11-02

- Q: What is the maximum number of seats one booking request may contain? → A: 6 seats per request (confirmed)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View a bus and its seats (Priority: P1)

A user opens the application, picks a bus, and sees a simple list of every seat on that bus. Each seat is clearly marked as either available or booked.

**Why this priority**: Without seeing seat availability, no booking decision can be made. It is also the smallest independently demonstrable slice.

**Independent Test**: With the mock data loaded, open a bus and verify the seat list shows exactly the bus's seat count, with seats marked booked exactly where a booking exists.

**Acceptance Scenarios**:

1. **Given** the mock data is loaded and bus "Bus A" has 20 seats and no bookings, **When** the user opens Bus A, **Then** exactly 20 seats numbered 1 to 20 are listed and all 20 are shown as available.
2. **Given** seat 5 of Bus A has an existing booking, **When** the user opens Bus A, **Then** seat 5 is shown as booked and the other 19 seats are shown as available.
3. **Given** the mock data is loaded, **When** the user opens the bus list, **Then** every mock bus is listed with its name and total seat count.
4. **Given** a bus identifier that does not exist, **When** the bus is requested, **Then** the request is rejected with a "not found" outcome (HTTP 404) and the UI shows a readable "bus not found" message.

---

### User Story 2 - Book one or more seats (Priority: P1)

A user selects one or more available seats on a bus and confirms the booking. The system records the booking against that user and bus, and the user is told it succeeded.

**Why this priority**: This is the core business action of the feature.

**Independent Test**: As a given mock user, select seats 3 and 4 on Bus A, confirm, and verify a success message appears and two booking records exist for that user and bus.

**Acceptance Scenarios**:

1. **Given** seats 3 and 4 of Bus A are available, **When** user "Asha" selects both and confirms, **Then** the booking succeeds (HTTP 201), one booking record is stored per seat with Asha's identifier, Bus A's identifier, and a booking datetime, and the UI shows a success message listing seats 3 and 4.
2. **Given** a user has selected no seats, **When** the user tries to confirm, **Then** the confirm action is unavailable in the UI, and a request with an empty seat list is rejected with a validation error (HTTP 422) and no booking is stored.
3. **Given** a request lists seat 3 twice, **When** it is submitted, **Then** it is rejected with a validation error (HTTP 422) and no booking is stored.
4. **Given** a request lists seat 21 on a 20-seat bus, **When** it is submitted, **Then** it is rejected with a business-rule error (HTTP 400) and no booking is stored; a request listing seat 0 or a negative number is rejected with a validation error (HTTP 422).
5. **Given** a request references a user or bus identifier that does not exist, **When** it is submitted, **Then** it is rejected with a "not found" outcome (HTTP 404) and no booking is stored.
6. **Given** a request lists more than 6 seats, **When** it is submitted, **Then** it is rejected with a validation error (HTTP 422) and no booking is stored.

---

### User Story 3 - Booked seats are protected and visible after booking (Priority: P1)

After a booking, the seats show as booked everywhere they are viewed, and nobody can book a seat that is already taken, even when requests happen at the same time.

**Why this priority**: Double-booking would make the feature unusable; seeing the result confirms the booking worked end to end.

**Independent Test**: Book seat 7, reload the seat list and confirm seat 7 shows as booked and cannot be selected; try to book seat 7 again and confirm it is refused.

**Acceptance Scenarios**:

1. **Given** user Asha has just booked seat 7 on Bus A, **When** the seat list for Bus A is viewed again (including after a full page reload), **Then** seat 7 is shown as booked and is not selectable.
2. **Given** seat 7 of Bus A is already booked, **When** any user submits a booking for seat 7, **Then** it is rejected with a conflict outcome (HTTP 409), no new booking is stored, and the UI shows a message that the seat is no longer available and refreshes the seat list.
3. **Given** a request for seats 8, 9, and 7 where only seat 7 is already booked, **When** it is submitted, **Then** the whole request is rejected (HTTP 409) and seats 8 and 9 remain unbooked (all-or-nothing).
4. **Given** seat 10 is available and two users submit a booking for it at the same moment, **When** both requests are processed, **Then** exactly one succeeds (HTTP 201) and the other receives a conflict outcome (HTTP 409); only one booking record exists for seat 10.
5. **Given** seat 7 of Bus A is booked, **When** the user views Bus B, **Then** seat 7 of Bus B is still shown as available (bookings are per bus).

---

### User Story 4 - Choose the booking user (Priority: P2)

Because this first feature has no sign-in, the user picks which mock user they are booking as before confirming a booking.

**Why this priority**: A booking needs a user identifier, but sign-in is out of scope; this keeps the feature usable and testable.

**Independent Test**: Choose "Ravi" from the user list, book a seat, and verify the stored booking carries Ravi's identifier.

**Acceptance Scenarios**:

1. **Given** the mock data is loaded, **When** the user opens the booking screen, **Then** all mock users are listed in a selector, and confirm is unavailable until one is chosen.
2. **Given** user Ravi is selected, **When** a booking is confirmed, **Then** the stored booking records Ravi's user identifier.

---

### Edge Cases

- Backend or database is unreachable while loading seats: the UI shows an error message with a retry action and no partial seat list.
- Backend or database is unreachable while booking: the UI shows an error message, keeps the user's selection, and no booking is stored.
- A seat is booked by someone else between the user viewing the list and confirming: the confirm is refused with a conflict outcome and the list is refreshed (see US3 scenario 2).
- User refreshes the page after selecting seats but before confirming: unconfirmed selections are discarded and nothing is stored.
- User clicks confirm repeatedly (double click): at most one booking per seat is stored; the repeat is refused as a conflict or ignored by the UI while a request is in flight.
- Malformed identifiers (non-numeric, empty, oversized text) and any identifier or seat number above 2,147,483,647: rejected with a validation error (HTTP 422) and no data change.
- Very small screens (320 px wide): the seat list remains fully usable without horizontal scrolling.

## Requirements *(mandatory)*

### Functional Requirements

**Data and seed data**

- **FR-001**: The system MUST store its data in a database named `bus_db` containing exactly three tables for this feature: one for buses, one for users, and one for bookings.
- **FR-002**: Each bus MUST have a unique identifier, a name, and a total seat count; seats are numbered 1 to the total seat count and are not stored as separate records.
- **FR-003**: Each user MUST have a unique identifier and a name.
- **FR-004**: Each booking MUST store a unique booking identifier, a bus identifier, a user identifier, a seat number, and a booking datetime.
- **FR-005**: The system MUST provide repeatable mock data containing at least 3 buses (including one with 20 seats) and at least 3 users (including "Asha" and "Ravi"), and an initially empty bookings table. Loading the mock data again MUST reset the tables to this same state.
- **FR-006**: The system MUST guarantee at the data level that a given seat on a given bus can have at most one booking.

**Bus information**

- **FR-007**: The system MUST provide a way to retrieve the list of all buses (identifier, name, total seat count).
- **FR-008**: The system MUST provide a way to retrieve one bus's details including every seat number from 1 to the total seat count with a status of `available` or `booked`, derived from stored bookings.
- **FR-009**: The system MUST provide a way to retrieve the list of users (identifier, name) for the user selector.

**Booking**

- **FR-010**: The system MUST provide a way to register a booking containing a bus identifier, a user identifier, and a list of 1 to 6 distinct seat numbers.
- **FR-011**: The system MUST validate every booking request before storing anything: the bus and user must exist, the list size must be 1 to 6, seat numbers must be whole numbers from 1 to the bus's total seat count, and seat numbers must not repeat.
- **FR-012**: The system MUST set the booking datetime itself at the time the booking is registered, in UTC; clients MUST NOT supply it. All seats in one request MUST share the same booking datetime.
- **FR-013**: The system MUST store one booking record per seat booked.
- **FR-014**: A booking request MUST be all-or-nothing: if any requested seat is unavailable or invalid, no booking record from that request is stored.
- **FR-015**: The system MUST reject a booking for an already-booked seat with a conflict outcome, including under simultaneous requests, so that no seat is ever double-booked.
- **FR-016**: A successful booking response MUST return the stored bookings (booking identifier, bus identifier, user identifier, seat number, booking datetime).
- **FR-017**: Every rejection MUST return a consistent, readable error body containing an error code and message, without exposing internal details such as stack traces or database messages.

**User interface**

- **FR-018**: The UI MUST show a bus list, and on choosing a bus show a simple list of all its seats, each labeled by seat number and visibly distinguished as available, booked, or selected (distinction MUST NOT rely on colour alone).
- **FR-019**: The UI MUST let the user select and deselect any number (1 to 6) of available seats; booked seats MUST NOT be selectable.
- **FR-020**: The UI MUST show a user selector and a confirm action that is enabled only when a user is chosen and at least 1 seat is selected.
- **FR-021**: On confirm, the UI MUST send the booking request, show a progress indication, and on success show a confirmation listing the booked seats and refresh the seat list so those seats appear as booked.
- **FR-022**: On failure, the UI MUST show a readable message distinguishing "seat no longer available", "invalid request", and "service unavailable", and MUST refresh the seat list after a conflict.
- **FR-023**: Seat state shown in the UI MUST always come from stored data; a page reload MUST show the same booked seats.
- **FR-024**: The UI MUST provide loading, empty, and error states for the bus list and the seat list.

### Non-Functional Requirements

- **NFR-001 (Performance)**: For a bus with up to 60 seats, retrieving its seat list MUST complete in under 300 ms at the 95th percentile on a local development machine with 1,000 stored bookings.
- **NFR-002 (Performance)**: Registering a booking of up to 6 seats MUST complete in under 500 ms at the 95th percentile on the same dataset.
- **NFR-003 (Consistency)**: Under 20 simultaneous requests to book the same seat, exactly 1 MUST succeed and 19 MUST be refused; the database MUST contain exactly 1 booking for that seat.
- **NFR-004 (Security)**: No credentials or secrets appear in source code, seed data, logs, or error responses; database credentials are supplied only through environment configuration. All inputs are validated server-side; no input can alter database structure or read other data.
- **NFR-005 (Reliability)**: No request, valid or invalid, may leave partial booking data; after any failed request the bookings table is identical to before the request.
- **NFR-006 (Responsiveness)**: The UI MUST be fully usable with no horizontal scrolling at viewport widths of 320 px, 768 px, and 1280 px.
- **NFR-007 (Lightweight)**: The initial page load MUST transfer no more than 200 KB of script (compressed) and show the bus list within 2 seconds on a local environment.
- **NFR-008 (Usability)**: A user can go from opening the application to a confirmed booking of one seat in 5 or fewer interactions (choose bus, choose user, select seat, confirm).
- **NFR-009 (Accessibility)**: Seats and actions are operable by keyboard alone and each seat has a text label stating its number and status.
- **NFR-010 (Maintainability and quality)**: Every requirement above has at least one automated test; backend line coverage is at least 85% and frontend line coverage is at least 80%; static checks (lint, type, security) report zero violations, per the project constitution.
- **NFR-011 (Reproducibility)**: From a fresh checkout with the environment file in place, a single documented command sequence starts the database, loads the mock data, and runs the application.

### Key Entities *(include if feature involves data)*

- **Bus**: A vehicle that can be booked. Attributes: identifier, name, total seat count. Seats are numbered 1 to total seat count.
- **User**: A person making a booking (mock, no sign-in). Attributes: identifier, name.
- **Booking**: One reserved seat on one bus for one user. Attributes: booking identifier, bus identifier, user identifier, seat number, booking datetime. Relationships: belongs to exactly one Bus and one User; a (bus, seat number) pair appears at most once.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can open a bus and see which seats are free or booked within 2 seconds of choosing it.
- **SC-002**: A user can complete a booking of 1 seat in 5 or fewer interactions and under 30 seconds.
- **SC-003**: 100% of seats booked through the UI show as booked on the next view of the same bus, including after a page reload.
- **SC-004**: 0 double-bookings occur across 20 simultaneous attempts to book the same seat (exactly 1 success).
- **SC-005**: 100% of invalid booking requests listed in the acceptance scenarios (empty list, duplicates, out-of-range seat, unknown bus or user, more than 6 seats) are refused with a readable message and leave stored data unchanged.
- **SC-006**: The seat list and booking flow are fully usable at 320 px, 768 px, and 1280 px widths without horizontal scrolling.
- **SC-007**: Every functional requirement is covered by at least one automated test, and all automated quality checks pass.

## Assumptions

- There is no sign-in; the user picks a mock user from a list. Authentication and authorisation are out of scope for this feature.
- "Temporary tables" means mock/seed data in ordinary tables of `bus_db` that can be reset at any time; no real production data is held.
- Seats are plain numbered seats (1 to N); seat types, rows, pricing, and seat-map layout are out of scope.
- Each booked seat is one booking record; a multi-seat request creates several records sharing one booking datetime.
- The maximum of 6 seats per request is confirmed (see Clarifications); changing it requires a later specification change.
- Bookings cannot be cancelled, edited, or paid for in this feature; these are future features.
- Trips, dates, routes, and schedules are out of scope; a seat is booked on a bus once, until the data is reset.
- Booking datetime is recorded in UTC and displayed as received; time-zone display is out of scope.
- Database credentials already exist in the project environment file (`DB_NAME`, `DB_USER`, `DB_PASSWORD`) and `DB_NAME` is expected to be `bus_db`.
- HTTP status codes in acceptance scenarios are stated so tests are binary, as required by the project constitution; the full interface contract is defined in the planning phase.
