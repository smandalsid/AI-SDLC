import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { login } from "../../src/api/auth";
import { ApiError } from "../../src/api/errors";
import { clearToken, getToken } from "../../src/api/session";
import { useAuthSession } from "../../src/hooks/useAuthSession";

vi.mock("../../src/api/auth", () => ({ login: vi.fn() }));

const loginMock = vi.mocked(login);

const SUCCESS = {
  access_token: "token-value",
  token_type: "bearer" as const,
  expires_at: "2026-01-15T11:00:00Z",
  user: { id: 1, name: "Asha" },
};

beforeEach(() => {
  vi.resetAllMocks();
});

afterEach(() => {
  clearToken();
});

describe("useAuthSession", () => {
  it("starts signed out", () => {
    const { result } = renderHook(() => useAuthSession());

    expect(result.current.state).toEqual({ status: "signedOut" });
  });

  it("stores the token and takes the user from the server after a successful sign-in", async () => {
    loginMock.mockResolvedValue(SUCCESS);
    const { result } = renderHook(() => useAuthSession());

    await act(async () => {
      await result.current.signIn("asha", "secret");
    });

    expect(loginMock).toHaveBeenCalledWith("asha", "secret");
    expect(result.current.state).toEqual({ status: "signedIn", user: { id: 1, name: "Asha" } });
    expect(getToken()).toBe("token-value");
  });

  it("leaves storage empty and the state signed out after a failed sign-in", async () => {
    loginMock.mockRejectedValue(new ApiError("credentials", 401, "invalid_credentials", "x"));
    const { result } = renderHook(() => useAuthSession());

    await act(async () => {
      await expect(result.current.signIn("asha", "wrong")).rejects.toBeInstanceOf(ApiError);
    });

    expect(result.current.state).toEqual({ status: "signedOut" });
    expect(getToken()).toBeNull();
  });

  it("clears the token and the state on sign-out", async () => {
    loginMock.mockResolvedValue(SUCCESS);
    const { result } = renderHook(() => useAuthSession());
    await act(async () => {
      await result.current.signIn("asha", "secret");
    });

    await act(async () => {
      await result.current.signOut();
    });

    expect(result.current.state).toEqual({ status: "signedOut" });
    expect(getToken()).toBeNull();
  });
});
