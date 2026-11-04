import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AuthState } from "../../src/hooks/useAuthSession";
import { AppHeader } from "../../src/components/AppHeader";
import { AuthContext } from "../../src/components/AuthProvider";

function renderHeader(state: AuthState, signOut = vi.fn().mockResolvedValue(undefined)) {
  render(
    <AuthContext.Provider value={{ state, signIn: vi.fn(), signOut }}>
      <AppHeader />
    </AuthContext.Provider>,
  );
  return signOut;
}

const SIGNED_IN: AuthState = { status: "signedIn", user: { id: 2, name: "Ravi" } };

describe("AppHeader", () => {
  it("shows the signed-in user's name and a Sign out button", () => {
    renderHeader(SIGNED_IN);

    expect(screen.getByRole("banner")).toHaveTextContent("Ravi");
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("calls sign-out when the button is clicked", async () => {
    const signOut = renderHeader(SIGNED_IN);

    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(signOut).toHaveBeenCalledOnce();
  });

  it.each([["{Enter}"], [" "]])("is reached with Tab and operated with the key %j", async (key) => {
    const signOut = renderHeader(SIGNED_IN);
    const user = userEvent.setup();

    await user.tab();
    expect(screen.getByRole("button", { name: "Sign out" })).toHaveFocus();
    await user.keyboard(key);

    expect(signOut).toHaveBeenCalledOnce();
  });

  it.each([[{ status: "signedOut" }], [{ status: "checking" }]] as [AuthState][])(
    "renders nothing unless the user is signed in (%j)",
    (state) => {
      renderHeader(state);

      expect(screen.queryByRole("banner")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    },
  );
});
