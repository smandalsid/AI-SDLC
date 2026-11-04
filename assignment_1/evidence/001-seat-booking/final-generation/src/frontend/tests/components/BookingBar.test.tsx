import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BookingBar } from "../../src/components/BookingBar";

interface Overrides {
  selectedSeats?: number[];
  hasUser?: boolean;
  submitting?: boolean;
  limitReached?: boolean;
  onConfirm?: () => void;
}

function renderBar(overrides: Overrides = {}): void {
  render(
    <BookingBar
      selectedSeats={overrides.selectedSeats ?? [3, 4]}
      hasUser={overrides.hasUser ?? true}
      submitting={overrides.submitting ?? false}
      limitReached={overrides.limitReached ?? false}
      onConfirm={overrides.onConfirm ?? vi.fn()}
    />,
  );
}

const confirm = (): HTMLElement => screen.getByRole("button", { name: "Confirm booking" });

describe("BookingBar", () => {
  it("shows the selected seat numbers", () => {
    renderBar();

    expect(screen.getByText("Selected seats: 3, 4")).toBeInTheDocument();
  });

  it("is enabled when a user and at least one seat are chosen", () => {
    renderBar();

    expect(confirm()).toBeEnabled();
  });

  it("is disabled without a user and hints to choose one", () => {
    renderBar({ hasUser: false });

    expect(confirm()).toBeDisabled();
    expect(screen.getByText("Choose a user to book as.")).toBeInTheDocument();
  });

  it("is disabled with no seats selected", () => {
    renderBar({ selectedSeats: [] });

    expect(confirm()).toBeDisabled();
    expect(screen.getByText("No seats selected.")).toBeInTheDocument();
  });

  it("is disabled while a request is in flight", () => {
    renderBar({ submitting: true });

    expect(confirm()).toBeDisabled();
  });

  it("explains the six-seat limit when it is reached", () => {
    renderBar({ limitReached: true });

    expect(screen.getByText("You can book up to 6 seats at a time.")).toBeInTheDocument();
  });

  it("calls the handler when confirmed", async () => {
    const onConfirm = vi.fn();
    renderBar({ onConfirm });

    await userEvent.click(confirm());

    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
