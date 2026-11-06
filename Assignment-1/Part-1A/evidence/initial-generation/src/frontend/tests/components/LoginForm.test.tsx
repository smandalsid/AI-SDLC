import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, type ApiErrorKind } from "../../src/api/errors";
import { LoginForm } from "../../src/components/LoginForm";

afterEach(() => {
  vi.restoreAllMocks();
});

function renderForm(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  render(<LoginForm onSubmit={onSubmit} />);
  return onSubmit;
}

async function fill(username: string, password: string): Promise<void> {
  if (username) await userEvent.type(screen.getByLabelText("Username"), username);
  if (password) await userEvent.type(screen.getByLabelText("Password"), password);
}

describe("LoginForm", () => {
  it("has labelled username and masked password fields", () => {
    renderForm();

    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
  });

  it("blocks an empty submit with a message for each empty field", async () => {
    const onSubmit = renderForm();

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("Enter your username.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toHaveAttribute("aria-invalid", "true");
  });

  it("blocks a submit that is missing only the password", async () => {
    const onSubmit = renderForm();
    await fill("asha", "");

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.queryByText("Enter your username.")).not.toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
  });

  it("blocks values longer than the server accepts", async () => {
    const onSubmit = renderForm();
    await fill("u".repeat(51), "p".repeat(129));

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("The username can have at most 50 characters.")).toBeInTheDocument();
    expect(screen.getByText("The password can have at most 128 characters.")).toBeInTheDocument();
  });

  it("submits the values exactly as typed", async () => {
    const onSubmit = renderForm();
    await fill(" Asha", "p a ss ");

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(onSubmit).toHaveBeenCalledWith(" Asha", "p a ss ");
  });

  it("disables the button while a request is in flight and sends only one request", async () => {
    const onSubmit = vi.fn().mockReturnValue(new Promise(() => undefined));
    renderForm(onSubmit);
    await fill("asha", "secret");

    await userEvent.dblClick(screen.getByRole("button", { name: "Sign in" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeDisabled();
  });

  it.each<[ApiErrorKind, number, string, RegExp]>([
    ["credentials", 401, "invalid_credentials", /Invalid username or password/],
    ["throttled", 429, "too_many_attempts", /Try again in 7 seconds/],
    ["invalid", 422, "validation_error", /username.*password/i],
    ["unavailable", 503, "service_unavailable", /Service unavailable/],
  ])("shows an alert for a %s failure and stays usable", async (kind, status, code, expected) => {
    const message = "Too many failed sign-in attempts. Try again in 7 seconds.";
    const onSubmit = vi.fn().mockRejectedValue(new ApiError(kind, status, code, message));
    renderForm(onSubmit);
    await fill("asha", "secret");

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(expected);
    await waitFor(() => expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled());
  });

  it("shows the server's throttle message with the seconds and lets the user try again", async () => {
    const message = "Too many failed sign-in attempts. Try again in 42 seconds.";
    const onSubmit = vi
      .fn()
      .mockRejectedValueOnce(new ApiError("throttled", 429, "too_many_attempts", message))
      .mockResolvedValueOnce(undefined);
    renderForm(onSubmit);
    await fill("asha", "secret");

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    const button = screen.getByRole("button", { name: "Sign in" });
    await waitFor(() => expect(button).toBeEnabled());
    expect(screen.getByLabelText("Username")).toHaveValue("asha");
    await userEvent.click(button);
    expect(onSubmit).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });

  it("is operable with the keyboard alone", async () => {
    const onSubmit = renderForm();

    await userEvent.tab();
    expect(screen.getByLabelText("Username")).toHaveFocus();
    await userEvent.keyboard("asha");
    await userEvent.tab();
    expect(screen.getByLabelText("Password")).toHaveFocus();
    await userEvent.keyboard("secret{Enter}");

    expect(onSubmit).toHaveBeenCalledWith("asha", "secret");
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Sign in" })).toHaveFocus();
  });

  it("never writes the values to the URL, console, or storage", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((method) =>
      vi.spyOn(console, method).mockImplementation(() => undefined),
    );
    renderForm();
    await fill("asha", "secret-value");

    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(window.location.href).not.toMatch(/asha|secret/);
    expect(sessionStorage.length + localStorage.length).toBe(0);
    for (const spy of spies) expect(JSON.stringify(spy.mock.calls)).not.toMatch(/secret/);
  });
});
