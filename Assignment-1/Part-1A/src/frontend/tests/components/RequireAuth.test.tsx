import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { me } from "../../src/api/auth";
import { ApiError } from "../../src/api/errors";
import { clearToken, getToken, setToken } from "../../src/api/session";
import { AuthProvider, useAuth } from "../../src/components/AuthProvider";
import { RequireAuth } from "../../src/components/RequireAuth";

vi.mock("../../src/api/auth", () => ({ login: vi.fn(), me: vi.fn() }));

const meMock = vi.mocked(me);
const mounted = vi.fn();

function Protected() {
  const { state } = useAuth();
  mounted();
  return <p>{state.status === "signedIn" ? `Hello ${state.user.name}` : "no user"}</p>;
}

function renderGuarded(route = "/"): void {
  render(
    <AuthProvider>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/login" element={<p>Sign in screen</p>} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<Protected />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
  clearToken();
});

describe("RequireAuth", () => {
  it("redirects to /login without a token and mounts nothing protected", async () => {
    renderGuarded();

    expect(await screen.findByText("Sign in screen")).toBeInTheDocument();
    expect(mounted).not.toHaveBeenCalled();
    expect(meMock).not.toHaveBeenCalled();
  });

  it("shows only a loading line until /auth/me answers, then renders the route", async () => {
    setToken("token-value");
    let answer: (user: { id: number; name: string }) => void = () => undefined;
    meMock.mockReturnValue(new Promise((resolve) => (answer = resolve)));

    renderGuarded();

    expect(screen.getByRole("status")).toHaveTextContent("Checking");
    expect(mounted).not.toHaveBeenCalled();
    answer({ id: 2, name: "Ravi" });
    expect(await screen.findByText("Hello Ravi")).toBeInTheDocument();
  });

  it("takes the user's name from the server, never from storage", async () => {
    setToken("token-value");
    meMock.mockResolvedValue({ id: 2, name: "Ravi" });

    renderGuarded();

    await screen.findByText("Hello Ravi");
    expect(JSON.stringify({ ...sessionStorage })).not.toContain("Ravi");
  });

  it("clears the token and redirects when /auth/me says the session is not valid", async () => {
    setToken("made-up-token");
    meMock.mockRejectedValue(new ApiError("unauthenticated", 401, "unauthenticated", "x"));

    renderGuarded();

    expect(await screen.findByText("Sign in screen")).toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(mounted).not.toHaveBeenCalled();
  });

  it("keeps the token and shows the service message when the check cannot be answered", async () => {
    setToken("token-value");
    meMock.mockRejectedValue(new ApiError("unavailable", 503, "service_unavailable", "x"));

    renderGuarded();

    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    expect(getToken()).toBe("token-value");
    expect(mounted).not.toHaveBeenCalled();
  });

  it("shows the sign-in screen without an error when sessionStorage is unavailable", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });

    renderGuarded();

    await waitFor(() => expect(screen.getByText("Sign in screen")).toBeInTheDocument());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
