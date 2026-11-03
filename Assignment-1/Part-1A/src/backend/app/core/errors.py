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


class UnauthenticatedError(AppError):
    """One message for every cause, so a caller cannot tell why a credential was refused."""

    code = "unauthenticated"
    default_message = "Authentication required."


class InvalidCredentialsError(AppError):
    code = "invalid_credentials"
    default_message = "Invalid username or password."


class TooManyAttemptsError(AppError):
    code = "too_many_attempts"

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Too many failed sign-in attempts. Try again in {retry_after_seconds} seconds."
        )


class DatabaseUnavailableError(Exception):
    """The database did not accept queries within the startup timeout."""
