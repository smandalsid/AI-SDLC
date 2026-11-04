from collections.abc import Sequence

import pytest
from app.core.errors import BusNotFoundError
from app.models.bus import Bus
from app.services.bus_service import BusService


class FakeBusReader:
    def __init__(self, buses: list[Bus]) -> None:
        self.buses = buses

    def list_page(self, page: int, page_size: int) -> Sequence[Bus]:
        start = (page - 1) * page_size
        return self.buses[start : start + page_size]

    def count(self) -> int:
        return len(self.buses)

    def get(self, bus_id: int) -> Bus | None:
        return next((bus for bus in self.buses if bus.id == bus_id), None)


class FakeBookedSeats:
    def __init__(self, booked: dict[int, set[int]]) -> None:
        self.booked = booked

    def booked_seat_numbers(self, bus_id: int) -> set[int]:
        return self.booked.get(bus_id, set())


def make_service(booked: dict[int, set[int]] | None = None) -> BusService:
    buses = [
        Bus(id=1, name="Bus A", total_seats=20),
        Bus(id=2, name="Bus B", total_seats=30),
        Bus(id=3, name="Bus C", total_seats=40),
    ]
    return BusService(FakeBusReader(buses), FakeBookedSeats(booked or {}))


def test_seats_are_numbered_one_to_total_in_order() -> None:
    detail = make_service().get_bus_detail(1)

    assert [seat.seat_number for seat in detail.seats] == list(range(1, 21))
    assert (detail.id, detail.name, detail.total_seats) == (1, "Bus A", 20)


def test_booked_numbers_map_to_booked_and_the_rest_to_available() -> None:
    detail = make_service({1: {5, 9}}).get_bus_detail(1)

    booked = [seat.seat_number for seat in detail.seats if seat.status == "booked"]
    available = [seat for seat in detail.seats if seat.status == "available"]
    assert booked == [5, 9]
    assert len(available) == 18


def test_unknown_bus_raises_bus_not_found() -> None:
    with pytest.raises(BusNotFoundError):
        make_service().get_bus_detail(99)


def test_list_returns_a_page_with_the_total() -> None:
    result = make_service().list_buses(page=2, page_size=2)

    assert [bus.id for bus in result.items] == [3]
    assert (result.page, result.page_size, result.total) == (2, 2, 3)
    assert result.items[0].name == "Bus C"
    assert result.items[0].total_seats == 40
