import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createBookings } from "../../src/api/bookings";
import { getBus } from "../../src/api/buses";
import { BusSeatsPage } from "../../src/pages/BusSeatsPage";
import { makeBusDetail, renderSignedIn } from "../helpers";

vi.mock("../../src/api/buses", () => ({ listBuses: vi.fn(), getBus: vi.fn() }));
vi.mock("../../src/api/bookings", () => ({ createBookings: vi.fn() }));

const createBookingsMock = vi.mocked(createBookings);
const MAX_TABS = 60;

function renderPage(): void {
  renderSignedIn("/buses/1", "/buses/:busId", <BusSeatsPage />);
}

const seat = (number: number): HTMLElement =>
  screen.getByRole("button", { name: new RegExp(`^Seat ${number},`) });

async function tabTo(user: ReturnType<typeof userEvent.setup>, find: () => HTMLElement) {
  for (let presses = 0; presses < MAX_TABS; presses += 1) {
    if (document.activeElement === find()) return;
    await user.tab();
  }
  throw new Error("the element was not reached with the Tab key");
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getBus).mockResolvedValue(makeBusDetail());
  createBookingsMock.mockResolvedValue({ bookings: [] });
});

describe("BusSeatsPage (keyboard only)", () => {
  it("books seats with Tab, Space, Enter and Tab to Confirm", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("button", { name: "Seat 1, available" });

    await tabTo(user, () => seat(3));
    await user.keyboard(" ");
    await tabTo(user, () => seat(4));
    await user.keyboard("{Enter}");
    expect(seat(3)).toHaveAttribute("aria-pressed", "true");
    expect(seat(4)).toHaveAttribute("aria-pressed", "true");

    await tabTo(user, () => screen.getByRole("button", { name: "Confirm booking" }));
    await user.keyboard("{Enter}");

    expect(createBookingsMock).toHaveBeenCalledWith({ bus_id: 1, seat_numbers: [3, 4] });
  });

  it("deselects a seat when Space is pressed on it again", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("button", { name: "Seat 1, available" });

    await tabTo(user, () => seat(1));
    await user.keyboard(" ");
    expect(seat(1)).toHaveAttribute("aria-pressed", "true");
    await user.keyboard(" ");

    expect(seat(1)).toHaveAttribute("aria-pressed", "false");
  });

  it("shows the 6-seat limit message when a seventh seat is chosen by keyboard", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("button", { name: "Seat 1, available" });
    await tabTo(user, () => seat(1));

    for (let number = 1; number <= 7; number += 1) {
      await user.keyboard(" ");
      if (number < 7) await user.tab();
    }

    expect(screen.getByText("You can book up to 6 seats at a time.")).toBeInTheDocument();
    expect(seat(7)).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("Selected seats: 1, 2, 3, 4, 5, 6")).toBeInTheDocument();
  });
});
