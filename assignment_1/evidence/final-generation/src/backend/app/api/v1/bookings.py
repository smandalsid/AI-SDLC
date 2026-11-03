from fastapi import APIRouter

from app.api.deps import BookingServiceDep
from app.api.schemas.booking import BookingCreate, BookingOut, BookingResult
from app.api.schemas.common import error_responses

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post(
    "",
    status_code=201,
    response_model=BookingResult,
    responses=error_responses(400, 404, 409, 422, 503),
)
def create_bookings(payload: BookingCreate, service: BookingServiceDep) -> BookingResult:
    created = service.book_seats(payload.bus_id, payload.user_id, payload.seat_numbers)
    return BookingResult(bookings=[BookingOut.model_validate(booking) for booking in created])
