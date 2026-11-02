import type { Seat } from "../api/types";

type SeatState = "available" | "booked" | "selected";

const LABELS: Record<SeatState, string> = {
  available: "Available",
  booked: "Booked",
  selected: "Selected",
};

interface SeatItemProps {
  seat: Seat;
  selected?: boolean;
  onToggle?: (seatNumber: number) => void;
}

export function SeatItem({ seat, selected = false, onToggle }: SeatItemProps) {
  const booked = seat.status === "booked";
  const state: SeatState = booked ? "booked" : selected ? "selected" : "available";
  return (
    <button
      type="button"
      className={`seat seat--${state}`}
      disabled={booked}
      aria-pressed={booked ? undefined : selected}
      aria-label={`Seat ${seat.seat_number}, ${state}`}
      onClick={() => onToggle?.(seat.seat_number)}
    >
      <span>{seat.seat_number}</span>
      <span className="seat__state">{LABELS[state]}</span>
    </button>
  );
}
