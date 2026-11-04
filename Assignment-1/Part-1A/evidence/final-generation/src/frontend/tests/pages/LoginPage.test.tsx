import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../src/api/errors";
import { AuthContext } from "../../src/components/AuthProvider";
import { LoginPage } from "../../src/pages/LoginPage";

function Where() {
  const location = useLocation();
  return <p data-testid="where">{`${location.pathname}${location.search}`}</p>;
}

const EXPIRY_MESSAGE = "Your session has expired. Please sign in again.";

function renderPage(
  signIn: (username: string, password: string) => Promise<void>,
  reason: "none" | "signedOut" | "expired" = "none",
) {
  const value = { state: { status: "signedOut" as const, reason }, signIn, signOut: vi.fn() };
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<p>Home page</p>} />
        </Routes>
        <Where />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

async function submit(username: string, password: string): Promise<void> {
  await userEvent.type(screen.getByLabelText("Username"), username);
  await userEvent.type(screen.getByLabelText("Password"), password);
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginPage", () => {
  it("shows the sign-in form under a heading", () => {
    renderPage(vi.fn());

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
  });

  it("signs in with the typed values and navigates to the bus list on success", async () => {
    const signIn = vi.fn().mockResolvedValue(undefined);
    renderPage(signIn);

    await submit("asha", "secret");

    expect(signIn).toHaveBeenCalledWith("asha", "secret");
    expect(await screen.findByText("Home page")).toBeInTheDocument();
    expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/);
  });

  it("shows the generic failure and stays on the page when the credentials are refused", async () => {
    const signIn = vi
      .fn()
      .mockRejectedValue(new ApiError("credentials", 401, "invalid_credentials", "x"));
    renderPage(signIn);

    await submit("asha", "wrong");

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username or password");
    expect(screen.queryByText("Home page")).not.toBeInTheDocument();
    expect(screen.getByTestId("where")).toHaveTextContent(/^\/login$/);
  });

  it("sends one request for a double click and keeps the credentials out of the URL", async () => {
    const signIn = vi.fn().mockReturnValue(new Promise(() => undefined));
    renderPage(signIn);
    await userEvent.type(screen.getByLabelText("Username"), "asha");
    await userEvent.type(screen.getByLabelText("Password"), "secret");

    await userEvent.dblClick(screen.getByRole("button", { name: "Sign in" }));

    expect(signIn).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("where")).toHaveTextContent(/^\/login$/);
  });
});

describe("LoginPage expiry message", () => {
  it("shows the expiry message as an alert after a session expired", () => {
    renderPage(vi.fn(), "expired");

    expect(screen.getByRole("alert")).toHaveTextContent(EXPIRY_MESSAGE);
  });

  it.each(["none", "signedOut"] as const)("shows no message for the reason %s", (reason) => {
    renderPage(vi.fn(), reason);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(EXPIRY_MESSAGE)).not.toBeInTheDocument();
  });
});
