from app.core.errors import BusNotFoundError
from app.repositories.protocols import BookedSeatReader, BusReader
from app.services.types import BusDetailView, BusSummary, PageResult, SeatView


class BusService:
    def __init__(self, buses: BusReader, bookings: BookedSeatReader) -> None:
        self.buses = buses
        self.bookings = bookings

    def list_buses(self, page: int, page_size: int) -> PageResult[BusSummary]:
        items = [
            BusSummary(id=bus.id, name=bus.name, total_seats=bus.total_seats)
            for bus in self.buses.list_page(page, page_size)
        ]
        return PageResult(items=items, page=page, page_size=page_size, total=self.buses.count())

    def get_bus_detail(self, bus_id: int) -> BusDetailView:
        bus = self.buses.get(bus_id)
        if bus is None:
            raise BusNotFoundError
        booked = self.bookings.booked_seat_numbers(bus_id)
        seats = [
            SeatView(seat_number=number, status="booked" if number in booked else "available")
            for number in range(1, bus.total_seats + 1)
        ]
        return BusDetailView(id=bus.id, name=bus.name, total_seats=bus.total_seats, seats=seats)
