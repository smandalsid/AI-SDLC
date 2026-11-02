import type { Seat, SeatStatus } from "../api/types";

const LABELS: Record<SeatStatus, string> = {
  available: "Available",
  booked: "Booked",
};

export function SeatItem({ seat }: { seat: Seat }) {
  const booked = seat.status === "booked";
  return (
    <button
      type="button"
      className={`seat seat--${seat.status}`}
      disabled={booked}
      aria-label={`Seat ${seat.seat_number}, ${seat.status}`}
    >
      <span>{seat.seat_number}</span>
      <span className="seat__state">{LABELS[seat.status]}</span>
    </button>
  );
}
