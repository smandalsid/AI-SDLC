import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { Bus, BusDetail, Seat, User } from "../src/api/types";

export function renderAt(route: string, path: string, element: ReactElement): RenderResult {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path={path} element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

export function makeBuses(): Bus[] {
  return [
    { id: 1, name: "Bus A", total_seats: 20 },
    { id: 2, name: "Bus B", total_seats: 30 },
  ];
}

export function makeUsers(): User[] {
  return [
    { id: 1, name: "Asha" },
    { id: 2, name: "Ravi" },
    { id: 3, name: "Meera" },
  ];
}

export function makeBusDetail(booked: number[] = []): BusDetail {
  const seats: Seat[] = Array.from({ length: 20 }, (_, index) => ({
    seat_number: index + 1,
    status: booked.includes(index + 1) ? "booked" : "available",
  }));
  return { id: 1, name: "Bus A", total_seats: 20, seats };
}

export function page<T>(items: T[]): { items: T[]; page: number; page_size: number; total: number } {
  return { items, page: 1, page_size: 20, total: items.length };
}
