import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../src/api/errors";
import { listBuses } from "../../src/api/buses";
import { BusListPage } from "../../src/pages/BusListPage";
import { makeBuses, page, renderSignedIn } from "../helpers";

vi.mock("../../src/api/buses", () => ({ listBuses: vi.fn(), getBus: vi.fn() }));

const listBusesMock = vi.mocked(listBuses);

function renderPage(): void {
  renderSignedIn("/", "/", <BusListPage />);
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("BusListPage", () => {
  it("shows a loading state while the buses load", () => {
    listBusesMock.mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("lists every bus with its seat count", async () => {
    listBusesMock.mockResolvedValue(page(makeBuses()));

    renderPage();

    expect(await screen.findByRole("link", { name: /Bus A/ })).toHaveAttribute("href", "/buses/1");
    expect(screen.getByRole("link", { name: /Bus B/ })).toHaveTextContent("30 seats");
  });

  it("shows an empty state when there are no buses", async () => {
    listBusesMock.mockResolvedValue(page([]));

    renderPage();

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("No buses"));
  });

  it("shows an error with Retry, and Retry loads the buses", async () => {
    listBusesMock
      .mockRejectedValueOnce(new ApiError("unavailable", 503, "service_unavailable", "down"))
      .mockResolvedValueOnce(page(makeBuses()));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("link", { name: /Bus A/ })).toBeInTheDocument();
    expect(listBusesMock).toHaveBeenCalledTimes(2);
  });
});
