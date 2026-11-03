class AppError(Exception):
    """Domain error that the API layer translates into an HTTP response."""

    code = "app_error"
    default_message = "The request could not be processed."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidSeatError(AppError):
    code = "invalid_seat"
    default_message = "One or more seat numbers do not exist on this bus."


class BusNotFoundError(AppError):
    code = "bus_not_found"
    default_message = "Bus not found."


class UserNotFoundError(AppError):
    code = "user_not_found"
    default_message = "User not found."


class SeatAlreadyBookedError(AppError):
    code = "seat_unavailable"
    default_message = "One or more requested seats are no longer available."


class DatabaseUnavailableError(Exception):
    """The database did not accept queries within the startup timeout."""
