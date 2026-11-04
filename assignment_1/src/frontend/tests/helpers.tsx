import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import type { Bus, BusDetail, Seat } from "../src/api/types";
import { AuthContext } from "../src/components/AuthProvider";

export function renderAt(route: string, path: string, element: ReactElement): RenderResult {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path={path} element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Renders inside an authentication context whose user is already signed in. */
export function renderSignedIn(route: string, path: string, element: ReactElement): RenderResult {
  const session = {
    state: { status: "signedIn" as const, user: { id: 1, name: "Asha" } },
    signIn: vi.fn(),
    signOut: vi.fn(),
  };
  return render(
    <AuthContext.Provider value={session}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={element} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

export function makeBuses(): Bus[] {
  return [
    { id: 1, name: "Bus A", total_seats: 20 },
    { id: 2, name: "Bus B", total_seats: 30 },
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
