import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../src/api/errors";
import { getBus } from "../../src/api/buses";
import { BusSeatsPage } from "../../src/pages/BusSeatsPage";
import { makeBusDetail, renderAt } from "../helpers";

vi.mock("../../src/api/buses", () => ({ listBuses: vi.fn(), getBus: vi.fn() }));

const getBusMock = vi.mocked(getBus);

function renderPage(route = "/buses/1"): void {
  renderAt(route, "/buses/:busId", <BusSeatsPage />);
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("BusSeatsPage (viewing)", () => {
  it("shows a loading state while the bus loads", () => {
    getBusMock.mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("lists every seat with booked seats marked", async () => {
    getBusMock.mockResolvedValue(makeBusDetail([5]));

    renderPage();

    expect(await screen.findByRole("button", { name: "Seat 5, booked" })).toBeDisabled();
    expect(screen.getAllByRole("button")).toHaveLength(20);
    expect(screen.getByRole("button", { name: "Seat 6, available" })).toBeEnabled();
    expect(getBusMock).toHaveBeenCalledWith(1);
  });

  it("shows an error with Retry and no partial seat list", async () => {
    getBusMock
      .mockRejectedValueOnce(new ApiError("unavailable", 503, "service_unavailable", "down"))
      .mockResolvedValueOnce(makeBusDetail());

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: "Seat 1, available" })).toBeInTheDocument();
  });

  it("shows a readable message when the bus does not exist", async () => {
    getBusMock.mockRejectedValue(new ApiError("invalid", 404, "bus_not_found", "missing"));

    renderPage("/buses/99");

    expect(await screen.findByRole("alert")).toHaveTextContent("Bus not found");
  });

  it.each(["abc", "0", "99999999999999999999"])(
    "shows bus not found for the malformed id %s without calling the API",
    (id) => {
      renderPage(`/buses/${id}`);

      expect(screen.getByRole("alert")).toHaveTextContent("Bus not found");
      expect(getBusMock).not.toHaveBeenCalled();
    },
  );
});
