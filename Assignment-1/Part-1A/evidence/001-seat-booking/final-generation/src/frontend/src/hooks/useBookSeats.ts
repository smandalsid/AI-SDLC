import { useCallback, useRef, useState } from "react";
import { createBookings } from "../api/bookings";
import { ApiError } from "../api/errors";
import type { BookingCreate } from "../api/types";

export type BookingState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success"; seats: number[] }
  | { status: "error"; error: unknown };

export type BookOutcome = { kind: "success" | "conflict" | "failed" | "ignored" };

export interface BookSeats {
  state: BookingState;
  submit: (request: BookingCreate) => Promise<BookOutcome>;
  reset: () => void;
}

export function useBookSeats(): BookSeats {
  const [state, setState] = useState<BookingState>({ status: "idle" });
  const inFlight = useRef(false);

  const submit = useCallback(async (request: BookingCreate): Promise<BookOutcome> => {
    if (inFlight.current) return { kind: "ignored" };
    inFlight.current = true;
    setState({ status: "submitting" });
    try {
      const result = await createBookings(request);
      setState({ status: "success", seats: result.bookings.map((booking) => booking.seat_number) });
      return { kind: "success" };
    } catch (error) {
      setState({ status: "error", error });
      return { kind: error instanceof ApiError && error.kind === "conflict" ? "conflict" : "failed" };
    } finally {
      inFlight.current = false;
    }
  }, []);

  const reset = useCallback(() => setState({ status: "idle" }), []);
  return { state, submit, reset };
}
