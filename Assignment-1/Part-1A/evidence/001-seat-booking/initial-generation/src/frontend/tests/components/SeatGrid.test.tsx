import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { SeatGrid } from "../../src/components/SeatGrid";
import type { Seat } from "../../src/api/types";

const seats: Seat[] = [
  { seat_number: 5, status: "booked" },
  { seat_number: 6, status: "available" },
  { seat_number: 7, status: "available" },
];

describe("SeatGrid", () => {
  it("renders one control per seat with an accessible name stating number and status", () => {
    render(<SeatGrid seats={seats} />);

    expect(screen.getAllByRole("button")).toHaveLength(3);
    expect(screen.getByRole("button", { name: "Seat 5, booked" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Seat 6, available" })).toBeInTheDocument();
  });

  it("disables booked seats and labels them with text, not colour alone", () => {
    render(<SeatGrid seats={seats} />);

    const booked = screen.getByRole("button", { name: "Seat 5, booked" });

    expect(booked).toBeDisabled();
    expect(within(booked).getByText("Booked")).toBeInTheDocument();
    expect(within(screen.getByRole("button", { name: "Seat 6, available" })).getByText("Available")).toBeInTheDocument();
  });

  it("is reachable by keyboard: Tab visits available seats and skips booked ones", async () => {
    render(<SeatGrid seats={seats} />);

    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Seat 6, available" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Seat 7, available" })).toHaveFocus();
  });
});
