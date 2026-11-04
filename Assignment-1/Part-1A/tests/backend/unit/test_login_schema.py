from typing import Any

import pytest
from app.api.schemas.auth import LoginRequest
from pydantic import ValidationError


def test_the_shortest_and_longest_allowed_values_are_accepted() -> None:
    shortest = LoginRequest(username="a", password="p")
    longest = LoginRequest(username="u" * 50, password="p" * 128)

    assert (shortest.username, shortest.password) == ("a", "p")
    assert (len(longest.username), len(longest.password)) == (50, 128)


@pytest.mark.parametrize("username", [" asha", "asha ", "ASHA", "Ünï cödé"])
def test_the_username_is_kept_exactly_as_typed(username: str) -> None:
    assert LoginRequest(username=username, password="p").username == username


@pytest.mark.parametrize("password", ["  spaced  ", "pässwörd-日本語", "UPPER lower"])
def test_the_password_is_kept_exactly_as_typed(password: str) -> None:
    assert LoginRequest(username="asha", password=password).password == password


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"username": "", "password": "p"}, "username"),
        ({"username": "u" * 51, "password": "p"}, "username"),
        ({"username": "asha", "password": ""}, "password"),
        ({"username": "asha", "password": "p" * 129}, "password"),
        ({"password": "p"}, "username"),
        ({"username": "asha"}, "password"),
        ({"username": 5, "password": "p"}, "username"),
        ({"username": "asha", "password": ["p"]}, "password"),
        ({"username": "asha", "password": "p", "remember": True}, "remember"),
    ],
    ids=[
        "empty-username",
        "long-username",
        "empty-password",
        "long-password",
        "missing-username",
        "missing-password",
        "non-string-username",
        "non-string-password",
        "extra-field",
    ],
)
def test_invalid_payloads_are_rejected_naming_the_field(
    payload: dict[str, Any], field: str
) -> None:
    with pytest.raises(ValidationError) as caught:
        LoginRequest.model_validate(payload)

    assert [error["loc"] for error in caught.value.errors()] == [(field,)]


def test_the_error_text_never_contains_the_submitted_values() -> None:
    submitted = "S3cret-" + "x" * 130

    with pytest.raises(ValidationError) as caught:
        LoginRequest(username="asha", password=submitted)

    assert "password" in str(caught.value)
    assert submitted not in str(caught.value)
