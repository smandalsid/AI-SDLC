import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

API = "/api/v1"
PROTECTED_CALLS = 100
ROUNDS = 5


def bearer(response: Response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def booking_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return int(session.execute(text("SELECT COUNT(*) FROM bookings")).scalar_one())


def test_after_the_response_one_hundred_protected_calls_all_return_401_and_no_data(
    client: TestClient, sign_in: Callable[[str], Response]
) -> None:
    headers = bearer(sign_in("asha"))
    assert client.post(f"{API}/auth/logout", headers=headers).status_code == 204

    responses = [
        client.get(f"{API}/buses" if index % 2 else f"{API}/buses/1", headers=headers)
        for index in range(PROTECTED_CALLS)
    ]

    assert [response.status_code for response in responses] == [401] * PROTECTED_CALLS
    assert not any("Bus A" in response.text or "seats" in response.text for response in responses)


def test_signing_in_again_gives_a_different_working_token_and_the_old_one_stays_refused(
    client: TestClient, sign_in: Callable[[str], Response]
) -> None:
    old = bearer(sign_in("asha"))
    client.post(f"{API}/auth/logout", headers=old)

    fresh = bearer(sign_in("asha"))

    assert fresh != old
    assert client.get(f"{API}/auth/me", headers=fresh).status_code == 200
    assert client.get(f"{API}/auth/me", headers=old).status_code == 401


def test_a_booking_with_the_old_token_after_sign_out_returns_401_and_stores_nothing(
    client: TestClient, session_factory: sessionmaker[Session], sign_in: Callable[[str], Response]
) -> None:
    headers = bearer(sign_in("asha"))
    client.post(f"{API}/auth/logout", headers=headers)

    response = client.post(
        f"{API}/bookings", json={"bus_id": 1, "seat_numbers": [3]}, headers=headers
    )

    assert response.status_code == 401
    assert booking_count(session_factory) == 0


def test_a_sign_out_and_a_booking_in_flight_together_never_store_a_booking_after_the_refusal(
    app: FastAPI, session_factory: sessionmaker[Session], sign_in: Callable[[str], Response]
) -> None:
    for seat in range(1, ROUNDS + 1):
        headers = bearer(sign_in("asha"))
        barrier = threading.Barrier(2)

        def sign_out(
            headers: dict[str, str] = headers, barrier: threading.Barrier = barrier
        ) -> int:
            with TestClient(app, raise_server_exceptions=False) as own:
                barrier.wait()
                return int(own.post(f"{API}/auth/logout", headers=headers).status_code)

        def book(
            headers: dict[str, str] = headers,
            barrier: threading.Barrier = barrier,
            seat: int = seat,
        ) -> int:
            with TestClient(app, raise_server_exceptions=False) as own:
                barrier.wait()
                body = {"bus_id": 1, "seat_numbers": [seat]}
                return int(own.post(f"{API}/bookings", json=body, headers=headers).status_code)

        with ThreadPoolExecutor(max_workers=2) as pool:
            out, booked = pool.submit(sign_out), pool.submit(book)
            logout_status, booking_status = out.result(), booked.result()

        assert logout_status == 204
        stored = booking_count(session_factory)
        assert (booking_status, stored) in {(201, 1), (401, 0)}
        with session_factory() as session:
            session.execute(text("DELETE FROM bookings"))
            session.commit()
