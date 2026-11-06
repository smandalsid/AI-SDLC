import { ApiError, describeApiError } from "../api/errors";
import type { BookingState } from "../hooks/useBookSeats";
import { StatusMessage } from "./StatusMessage";

export function BookingFeedback({ state }: { state: BookingState }) {
  if (state.status === "idle") return null;
  if (state.status === "submitting") {
    return <StatusMessage variant="loading" message="Booking seats…" />;
  }
  if (state.status === "success") {
    const noun = state.seats.length === 1 ? "seat" : "seats";
    return <StatusMessage variant="success" message={`Booked ${noun} ${state.seats.join(", ")}.`} />;
  }
  const conflict = state.error instanceof ApiError && state.error.kind === "conflict";
  return (
    <StatusMessage variant={conflict ? "conflict" : "error"} message={describeApiError(state.error)} />
  );
}
