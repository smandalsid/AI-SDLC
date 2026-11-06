import { MAX_SEATS_PER_BOOKING } from "../hooks/useSeatSelection";

interface BookingBarProps {
  selectedSeats: number[];
  hasUser: boolean;
  submitting: boolean;
  limitReached: boolean;
  onConfirm: () => void;
}

export function BookingBar({
  selectedSeats,
  hasUser,
  submitting,
  limitReached,
  onConfirm,
}: BookingBarProps) {
  const canConfirm = hasUser && selectedSeats.length > 0 && !submitting;
  return (
    <div className="booking-bar">
      <p>
        {selectedSeats.length === 0
          ? "No seats selected."
          : `Selected seats: ${selectedSeats.join(", ")}`}
      </p>
      {!hasUser && <p>Choose a user to book as.</p>}
      {limitReached && <p>You can book up to {MAX_SEATS_PER_BOOKING} seats at a time.</p>}
      <button type="button" className="button" disabled={!canConfirm} onClick={onConfirm}>
        Confirm booking
      </button>
    </div>
  );
}
