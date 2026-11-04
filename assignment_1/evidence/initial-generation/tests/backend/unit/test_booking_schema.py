import pytest
from app.api.schemas.booking import BookingCreate
from pydantic import ValidationError


def build(**overrides: object) -> dict[str, object]:
    return {"bus_id": 1, "seat_numbers": [3], **overrides}


@pytest.mark.parametrize("seats", [[1], [1, 2, 3, 4, 5, 6], [2147483647]])
def test_valid_seat_lists_are_accepted(seats: list[int]) -> None:
    assert BookingCreate.model_validate(build(seat_numbers=seats)).seat_numbers == seats


@pytest.mark.parametrize(
    "seats",
    [[], [1, 2, 3, 4, 5, 6, 7], [3, 3], [0], [-1], [2147483648], ["3"], [3.0], [3.5], [True]],
)
def test_invalid_seat_lists_are_rejected(seats: list[object]) -> None:
    with pytest.raises(ValidationError):
        BookingCreate.model_validate(build(seat_numbers=seats))


@pytest.mark.parametrize("value", [0, -1, 2147483648, "1", 1.5, None])
def test_invalid_bus_ids_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        BookingCreate.model_validate(build(bus_id=value))


@pytest.mark.parametrize("value", [1, 2, 999, 0, "1", None])
def test_a_user_id_is_rejected_whatever_its_value(value: object) -> None:
    with pytest.raises(ValidationError):
        BookingCreate.model_validate(build(user_id=value))


def test_the_schema_has_no_user_id_field() -> None:
    assert "user_id" not in BookingCreate.model_fields


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        BookingCreate.model_validate(build(booked_at="2026-01-01T00:00:00Z"))
