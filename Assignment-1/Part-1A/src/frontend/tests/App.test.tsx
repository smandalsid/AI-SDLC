import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listBuses } from "../src/api/buses";
import { App } from "../src/App";
import { AuthContext } from "../src/components/AuthProvider";
import { makeBuses, page } from "./helpers";

vi.mock("../src/api/buses", () => ({ listBuses: vi.fn(), getBus: vi.fn() }));
vi.mock("../src/api/auth", () => ({ login: vi.fn() }));

const listBusesMock = vi.mocked(listBuses);

function renderApp(route: string, signedIn: boolean): void {
  const state = signedIn
    ? { status: "signedIn" as const, user: { id: 1, name: "Asha" } }
    : { status: "signedOut" as const };
  const value = { state, signIn: vi.fn(), signOut: vi.fn() };
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  listBusesMock.mockResolvedValue(page(makeBuses()));
});

describe("App routes for sign-in", () => {
  it("renders the sign-in page at /login", async () => {
    renderApp("/login", false);

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("redirects a signed-in user who visits /login to the bus list", async () => {
    renderApp("/login", true);

    expect(await screen.findByRole("heading", { name: "Buses" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
  });
});
