import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { logout, me } from "../src/api/auth";
import { getBus, listBuses } from "../src/api/buses";
import { clearToken, getToken, setToken } from "../src/api/session";
import { App } from "../src/App";
import { AuthContext, AuthProvider } from "../src/components/AuthProvider";
import { makeBuses, makeBusDetail, page } from "./helpers";

vi.mock("../src/api/buses", () => ({ listBuses: vi.fn(), getBus: vi.fn() }));
vi.mock("../src/api/auth", () => ({ login: vi.fn(), logout: vi.fn(), me: vi.fn() }));

const listBusesMock = vi.mocked(listBuses);
const getBusMock = vi.mocked(getBus);
const logoutMock = vi.mocked(logout);
const meMock = vi.mocked(me);

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

describe("App routes for a signed-out visitor", () => {
  it.each(["/", "/buses/1", "/foo"])("shows only the sign-in screen at %s", async (route) => {
    renderApp(route, false);

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText("Page not found.")).not.toBeInTheDocument();
    expect(listBusesMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("link", { name: /Bus A/ })).not.toBeInTheDocument();
  });
});

describe("App routes for a signed-in user", () => {
  it("shows the bus list at /", async () => {
    renderApp("/", true);

    expect(await screen.findByRole("link", { name: /Bus A/ })).toBeInTheDocument();
  });

  it("shows the not-found page for an unknown address", async () => {
    renderApp("/foo", true);

    expect(await screen.findByText("Page not found.")).toBeInTheDocument();
  });
});

describe("App header for a signed-in user", () => {
  it.each(["/", "/buses/1", "/foo"])("shows the name and Sign out at %s", async (route) => {
    getBusMock.mockResolvedValue(makeBusDetail());
    renderApp(route, true);

    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.getByRole("banner")).toHaveTextContent("Asha");
  });
});

describe("App sign-out", () => {
  function renderWithRealSession(route: string): void {
    setToken("token-value");
    meMock.mockResolvedValue({ id: 1, name: "Asha" });
    getBusMock.mockResolvedValue(makeBusDetail());
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={[route]}>
          <App />
        </MemoryRouter>
      </AuthProvider>,
    );
  }

  afterEach(() => {
    clearToken();
  });

  it.each(["/", "/buses/1", "/foo"])(
    "at %s calls the endpoint, clears storage and shows only the sign-in screen",
    async (route) => {
      logoutMock.mockResolvedValue(undefined);
      renderWithRealSession(route);

      await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));

      expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
      expect(logoutMock).toHaveBeenCalledOnce();
      expect(getToken()).toBeNull();
      expect(screen.queryByRole("link", { name: /Bus A/ })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Seat \d+/ })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    },
  );

  it("shows the sign-in screen even when the sign-out call fails", async () => {
    logoutMock.mockRejectedValue(new Error("network"));
    renderWithRealSession("/");

    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });
});
