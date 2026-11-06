import { request } from "./client";
import type { BookingCreate, BookingResult } from "./types";

export function createBookings(booking: BookingCreate): Promise<BookingResult> {
  return request<BookingResult>("/bookings", { method: "POST", body: booking });
}
