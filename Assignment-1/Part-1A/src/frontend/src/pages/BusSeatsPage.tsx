import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, describeApiError } from "../api/errors";
import type { BusDetail } from "../api/types";
import { BookingBar } from "../components/BookingBar";
import { BookingFeedback } from "../components/BookingFeedback";
import { SeatGrid } from "../components/SeatGrid";
import { StatusMessage } from "../components/StatusMessage";
import { UserSelect } from "../components/UserSelect";
import { useBookSeats } from "../hooks/useBookSeats";
import { useBusDetail } from "../hooks/useBusDetail";
import { useSeatSelection } from "../hooks/useSeatSelection";
import { useUsers } from "../hooks/useUsers";

const ID_PATTERN = /^[1-9]\d*$/;
const MAX_ID = 2_147_483_647;

function parseBusId(raw: string | undefined): number | null {
  if (raw === undefined || !ID_PATTERN.test(raw)) return null;
  const value = Number(raw);
  return value <= MAX_ID ? value : null;
}

function BusSeatsContent({ bus, onRefresh }: { bus: BusDetail; onRefresh: () => void }) {
  const users = useUsers();
  const [userId, setUserId] = useState<number | null>(null);
  const selection = useSeatSelection(bus.seats);
  const booking = useBookSeats();

  async function confirm(): Promise<void> {
    if (userId === null) return;
    const request = { bus_id: bus.id, user_id: userId, seat_numbers: selection.selected };
    const outcome = await booking.submit(request);
    if (outcome.kind === "success") selection.clear();
    // Success and conflict both mean the stored seats changed, so re-read them.
    if (outcome.kind === "success" || outcome.kind === "conflict") onRefresh();
  }

  function toggle(seatNumber: number): void {
    booking.reset();
    selection.toggle(seatNumber);
  }

  return (
    <>
      <h1>{bus.name}</h1>
      <p>{bus.total_seats} seats</p>
      <UserSelect users={users} value={userId} onChange={setUserId} />
      <SeatGrid seats={bus.seats} selected={selection.selected} onToggle={toggle} />
      <BookingBar
        selectedSeats={selection.selected}
        hasUser={userId !== null}
        submitting={booking.state.status === "submitting"}
        limitReached={selection.limitReached}
        onConfirm={() => void confirm()}
      />
      <BookingFeedback state={booking.state} />
    </>
  );
}

function BusSeats({ busId }: { busId: number }) {
  const bus = useBusDetail(busId);

  if (bus.status === "loading") return <StatusMessage variant="loading" message="Loading seats…" />;
  if (bus.status === "error") {
    if (bus.error instanceof ApiError && bus.error.status === 404) {
      return <StatusMessage variant="error" message="Bus not found." />;
    }
    return (
      <StatusMessage variant="error" message={describeApiError(bus.error)} onRetry={bus.refresh} />
    );
  }
  return <BusSeatsContent bus={bus.data} onRefresh={bus.refresh} />;
}

export function BusSeatsPage() {
  const busId = parseBusId(useParams().busId);

  return (
    <main className="page">
      <Link to="/">← All buses</Link>
      {busId === null ? (
        <StatusMessage variant="error" message="Bus not found." />
      ) : (
        <BusSeats busId={busId} />
      )}
    </main>
  );
}
