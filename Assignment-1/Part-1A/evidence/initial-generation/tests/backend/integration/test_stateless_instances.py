from collections.abc import Callable, Mapping

from fastapi import FastAPI
from fastapi.testclient import TestClient

API = "/api/v1"
WRONG = "wrong-password"


def test_two_instances_give_the_same_answer_to_the_same_token(
    make_app: Callable[[], FastAPI], credentials: Mapping[str, str]
) -> None:
    first, second = TestClient(make_app()), TestClient(make_app())
    token = first.post(
        f"{API}/auth/login", json={"username": "asha", "password": credentials["asha"]}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    answers = [client.get(f"{API}/auth/me", headers=headers) for client in (first, second)]

    assert [answer.status_code for answer in answers] == [200, 200]
    assert answers[0].json() == answers[1].json() == {"id": 1, "name": "Asha"}


def test_a_sign_out_on_one_instance_ends_the_session_on_the_other(
    make_app: Callable[[], FastAPI], credentials: Mapping[str, str]
) -> None:
    first, second = TestClient(make_app()), TestClient(make_app())
    token = second.post(
        f"{API}/auth/login", json={"username": "asha", "password": credentials["asha"]}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert first.post(f"{API}/auth/logout", headers=headers).status_code == 204

    assert [
        client.get(f"{API}/auth/me", headers=headers).status_code for client in (first, second)
    ] == [
        401,
        401,
    ]


def test_the_throttle_count_is_shared_by_two_instances(
    make_app: Callable[[], FastAPI], credentials: Mapping[str, str]
) -> None:
    first, second = TestClient(make_app()), TestClient(make_app())
    for client, times in [(first, 2), (second, 3)]:
        for _ in range(times):
            assert (
                client.post(
                    f"{API}/auth/login", json={"username": "ravi", "password": WRONG}
                ).status_code
                == 401
            )

    answers = [
        client.post(
            f"{API}/auth/login", json={"username": "ravi", "password": credentials["ravi"]}
        ).status_code
        for client in (first, second)
    ]

    assert answers == [429, 429]
