import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getBus } from "../../src/api/buses";
import { createBookings } from "../../src/api/bookings";
import { ApiError } from "../../src/api/errors";
import type { BookingResult } from "../../src/api/types";
import { listUsers } from "../../src/api/users";
import { BusSeatsPage } from "../../src/pages/BusSeatsPage";
import { makeBusDetail, makeUsers, page } from "../helpers";

vi.mock("../../src/api/buses", () => ({ listBuses: vi.fn(), getBus: vi.fn() }));
vi.mock("../../src/api/users", () => ({ listUsers: vi.fn() }));
vi.mock("../../src/api/bookings", () => ({ createBookings: vi.fn() }));

const getBusMock = vi.mocked(getBus);
const createBookingsMock = vi.mocked(createBookings);

const result: BookingResult = {
  bookings: [3, 4].map((seat, index) => ({
    id: index + 1,
    bus_id: 1,
    user_id: 2,
    seat_number: seat,
    booked_at: "2026-01-15T10:30:00Z",
  })),
};

function renderPage(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={["/buses/1"]}>
      <Routes>
        <Route path="/buses/:busId" element={<BusSeatsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const seat = (number: number, state = "available"): Promise<HTMLElement> =>
  screen.findByRole("button", { name: `Seat ${number}, ${state}` });
const confirm = (): HTMLElement => screen.getByRole("button", { name: "Confirm booking" });

async function chooseRaviAndSeats(...seats: number[]): Promise<void> {
  await userEvent.selectOptions(await screen.findByLabelText("Booking as"), "Ravi");
  for (const number of seats) await userEvent.click(await seat(number));
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(listUsers).mockResolvedValue(page(makeUsers()));
  getBusMock.mockResolvedValue(makeBusDetail());
});

describe("BusSeatsPage (booking)", () => {
  it("sends the booking, shows progress, then success, and re-reads the seats", async () => {
    let finish: (value: BookingResult) => void = () => undefined;
    createBookingsMock.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    renderPage();
    await chooseRaviAndSeats(3, 4);

    await userEvent.click(confirm());

    expect(createBookingsMock).toHaveBeenCalledWith({ bus_id: 1, user_id: 2, seat_numbers: [3, 4] });
    expect(screen.getByRole("status")).toHaveTextContent("Booking seats");
    expect(confirm()).toBeDisabled();

    getBusMock.mockResolvedValue(makeBusDetail([3, 4]));
    finish(result);

    expect(await screen.findByText("Booked seats 3, 4.")).toBeInTheDocument();
    expect(await seat(3, "booked")).toBeDisabled();
    expect(await seat(4, "booked")).toBeDisabled();
    expect(getBusMock).toHaveBeenCalledTimes(2);
    expect(screen.getByText("No seats selected.")).toBeInTheDocument();
  });

  it("sends only one request when Confirm is clicked twice", async () => {
    createBookingsMock.mockReturnValue(new Promise(() => undefined));
    renderPage();
    await chooseRaviAndSeats(3);

    await userEvent.click(confirm());
    await userEvent.click(confirm());

    expect(createBookingsMock).toHaveBeenCalledTimes(1);
  });

  it("cannot select a seventh seat", async () => {
    renderPage();
    await chooseRaviAndSeats(1, 2, 3, 4, 5, 6);

    await userEvent.click(await seat(7));

    expect(await seat(7)).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("Selected seats: 1, 2, 3, 4, 5, 6")).toBeInTheDocument();
    expect(screen.getByText("You can book up to 6 seats at a time.")).toBeInTheDocument();
  });

  it("disables Confirm without a user or without seats", async () => {
    renderPage();
    await userEvent.click(await seat(3, "available"));
    expect(confirm()).toBeDisabled();

    await userEvent.selectOptions(screen.getByLabelText("Booking as"), "Ravi");
    expect(confirm()).toBeEnabled();
    await userEvent.click(await seat(3, "selected"));
    expect(confirm()).toBeDisabled();
  });

  it("discards an unconfirmed selection when the page is reloaded", async () => {
    const first = renderPage();
    await chooseRaviAndSeats(3, 4);
    first.unmount();

    renderPage();

    expect(await seat(3)).toHaveAttribute("aria-pressed", "false");
    await waitFor(() => expect(confirm()).toBeDisabled());
    expect(screen.getByText("No seats selected.")).toBeInTheDocument();
    expect(createBookingsMock).not.toHaveBeenCalled();
  });
});

describe("BusSeatsPage (failed bookings)", () => {
  it("on a conflict shows an alert, refreshes the seats, and drops the taken seat", async () => {
    createBookingsMock.mockRejectedValue(
      new ApiError("conflict", 409, "seat_unavailable", "taken"),
    );
    renderPage();
    await chooseRaviAndSeats(3, 4);
    getBusMock.mockResolvedValue(makeBusDetail([3]));

    await userEvent.click(confirm());

    expect(await screen.findByRole("alert")).toHaveTextContent("Seat no longer available");
    expect(await seat(3, "booked")).toBeDisabled();
    expect(getBusMock).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Selected seats: 4")).toBeInTheDocument();
  });

  it.each([
    ["a 503 response", new ApiError("unavailable", 503, "service_unavailable", "down")],
    ["a network failure", new ApiError("unavailable", 0, "network_error", "unreachable")],
  ])("on %s shows Service unavailable and keeps the selection", async (_label, error) => {
    createBookingsMock.mockRejectedValue(error);
    renderPage();
    await chooseRaviAndSeats(3, 4);

    await userEvent.click(confirm());

    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(screen.getByText("Selected seats: 3, 4")).toBeInTheDocument();
    expect(screen.queryByText(/^Booked seat/)).not.toBeInTheDocument();
    expect(getBusMock).toHaveBeenCalledTimes(1);
    expect(confirm()).toBeEnabled();
  });

  it.each([400, 422])("on a %i response shows Invalid request", async (status) => {
    createBookingsMock.mockRejectedValue(new ApiError("invalid", status, "validation_error", "bad"));
    renderPage();
    await chooseRaviAndSeats(3);

    await userEvent.click(confirm());

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid request");
  });
});
