import type { Seat } from "../api/types";
import { SeatItem } from "./SeatItem";

interface SeatGridProps {
  seats: Seat[];
  selected?: number[];
  onToggle?: (seatNumber: number) => void;
}

export function SeatGrid({ seats, selected = [], onToggle }: SeatGridProps) {
  return (
    <ul className="seat-grid">
      {seats.map((seat) => (
        <li key={seat.seat_number}>
          <SeatItem
            seat={seat}
            selected={selected.includes(seat.seat_number)}
            onToggle={onToggle}
          />
        </li>
      ))}
    </ul>
  );
}
