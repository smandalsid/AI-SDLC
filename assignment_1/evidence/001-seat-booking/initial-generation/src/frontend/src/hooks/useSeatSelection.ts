import { useState } from "react";
import type { Seat } from "../api/types";

export const MAX_SEATS_PER_BOOKING = 6;

export interface SeatSelection {
  selected: number[];
  limitReached: boolean;
  toggle: (seatNumber: number) => void;
  clear: () => void;
}

/** Selection lives only in component state; it is never persisted, so a reload discards it. */
export function useSeatSelection(seats: Seat[], maxSeats = MAX_SEATS_PER_BOOKING): SeatSelection {
  const [picked, setPicked] = useState<number[]>([]);
  const available = new Set(
    seats.filter((seat) => seat.status === "available").map((seat) => seat.seat_number),
  );
  // Seats that became booked since they were picked drop out of the selection.
  const selected = picked.filter((number) => available.has(number)).sort((a, b) => a - b);

  function toggle(seatNumber: number): void {
    if (!available.has(seatNumber)) return;
    setPicked((previous) => {
      const current = previous.filter((number) => available.has(number));
      if (current.includes(seatNumber)) return current.filter((number) => number !== seatNumber);
      return current.length >= maxSeats ? current : [...current, seatNumber];
    });
  }

  return { selected, limitReached: selected.length >= maxSeats, toggle, clear: () => setPicked([]) };
}
