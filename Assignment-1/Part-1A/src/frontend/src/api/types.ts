// Mirrors specs/002-user-authentication/contracts/openapi.yaml.

export type SeatStatus = "available" | "booked";

export interface Seat {
  seat_number: number;
  status: SeatStatus;
}

export interface Bus {
  id: number;
  name: string;
  total_seats: number;
}

export interface BusDetail extends Bus {
  seats: Seat[];
}

export interface User {
  id: number;
  name: string;
}

export interface AuthUser {
  id: number;
  name: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: AuthUser;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface BookingCreate {
  bus_id: number;
  user_id: number;
  seat_numbers: number[];
}

export interface Booking {
  id: number;
  bus_id: number;
  user_id: number;
  seat_number: number;
  booked_at: string;
}

export interface BookingResult {
  bookings: Booking[];
}

export interface ErrorBody {
  code: string;
  message: string;
}

export interface ErrorResponse {
  error: ErrorBody;
}
