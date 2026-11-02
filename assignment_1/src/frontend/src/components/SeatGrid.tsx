import type { Seat } from "../api/types";
import { SeatItem } from "./SeatItem";

export function SeatGrid({ seats }: { seats: Seat[] }) {
  return (
    <ul className="seat-grid">
      {seats.map((seat) => (
        <li key={seat.seat_number}>
          <SeatItem seat={seat} />
        </li>
      ))}
    </ul>
  );
}
