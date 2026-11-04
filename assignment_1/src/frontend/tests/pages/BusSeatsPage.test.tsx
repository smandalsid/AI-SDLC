import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../src/api/errors";
import { getBus } from "../../src/api/buses";
import { listUsers } from "../../src/api/users";
import { BusSeatsPage } from "../../src/pages/BusSeatsPage";
import { makeBusDetail, makeUsers, page, renderSignedIn } from "../helpers";

vi.mock("../../src/api/buses", () => ({ listBuses: vi.fn(), getBus: vi.fn() }));
vi.mock("../../src/api/users", () => ({ listUsers: vi.fn() }));

const getBusMock = vi.mocked(getBus);
const listUsersMock = vi.mocked(listUsers);

function renderPage(route = "/buses/1"): void {
  renderSignedIn(route, "/buses/:busId", <BusSeatsPage />);
}

beforeEach(() => {
  vi.resetAllMocks();
  listUsersMock.mockResolvedValue(page(makeUsers()));
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
    expect(screen.getAllByRole("button", { name: /^Seat \d+,/ })).toHaveLength(20);
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

describe("BusSeatsPage (choosing the user)", () => {
  it("lists the users in a selector once the seats are shown", async () => {
    getBusMock.mockResolvedValue(makeBusDetail());

    renderPage();

    const select = await screen.findByLabelText("Booking as");
    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Choose a user", "Asha", "Ravi", "Meera"]);
    expect(select).toHaveValue("");
  });

  it("keeps the chosen user selected", async () => {
    getBusMock.mockResolvedValue(makeBusDetail());
    renderPage();

    const select = await screen.findByLabelText("Booking as");
    await userEvent.selectOptions(select, "Ravi");

    expect(select).toHaveValue("2");
  });
});
