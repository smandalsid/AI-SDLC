import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { login, logout, me } from "../../src/api/auth";
import { ApiError } from "../../src/api/errors";
import { clearToken, expire, getToken, setToken } from "../../src/api/session";
import { useAuthSession } from "../../src/hooks/useAuthSession";

vi.mock("../../src/api/auth", () => ({ login: vi.fn(), logout: vi.fn(), me: vi.fn() }));

const loginMock = vi.mocked(login);
const logoutMock = vi.mocked(logout);
const meMock = vi.mocked(me);

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
    logoutMock.mockResolvedValue(undefined);
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

describe("useAuthSession sign-out", () => {
  async function signedIn() {
    loginMock.mockResolvedValue(SUCCESS);
    const hook = renderHook(() => useAuthSession());
    await act(async () => {
      await hook.result.current.signIn("asha", "secret");
    });
    return hook;
  }

  it("calls the sign-out endpoint once, while the token is still stored", async () => {
    let tokenDuringCall: string | null = null;
    logoutMock.mockImplementation(() => {
      tokenDuringCall = getToken();
      return Promise.resolve();
    });
    const { result } = await signedIn();

    await act(async () => {
      await result.current.signOut();
    });

    expect(logoutMock).toHaveBeenCalledTimes(1);
    expect(tokenDuringCall).toBe("token-value");
    expect(getToken()).toBeNull();
    expect(result.current.state).toEqual({ status: "signedOut" });
  });

  it.each([
    ["a network failure", new ApiError("unavailable", 0, "network_error", "unreachable")],
    ["a 401", new ApiError("unauthenticated", 401, "unauthenticated", "x")],
    ["a 503", new ApiError("unavailable", 503, "service_unavailable", "down")],
  ])("still clears the storage and the state after %s", async (_label, error) => {
    logoutMock.mockRejectedValue(error);
    const { result } = await signedIn();

    await act(async () => {
      await result.current.signOut();
    });

    expect(getToken()).toBeNull();
    expect(result.current.state).toEqual({ status: "signedOut" });
  });
});

describe("useAuthSession with a stored token", () => {
  it("checks the token with the server and takes the user from the answer", async () => {
    setToken("token-value");
    meMock.mockResolvedValue({ id: 2, name: "Ravi" });

    const { result } = renderHook(() => useAuthSession());

    expect(result.current.state).toEqual({ status: "checking" });
    await vi.waitFor(() =>
      expect(result.current.state).toEqual({ status: "signedIn", user: { id: 2, name: "Ravi" } }),
    );
  });

  it("forgets a token the server does not accept", async () => {
    setToken("made-up-token");
    meMock.mockRejectedValue(new ApiError("unauthenticated", 401, "unauthenticated", "x"));

    const { result } = renderHook(() => useAuthSession());

    await vi.waitFor(() => expect(result.current.state).toEqual({ status: "signedOut" }));
    expect(getToken()).toBeNull();
  });

  it("keeps the token when the check cannot be answered", async () => {
    setToken("token-value");
    meMock.mockRejectedValue(new ApiError("unavailable", 503, "service_unavailable", "x"));

    const { result } = renderHook(() => useAuthSession());

    await vi.waitFor(() => expect(result.current.state).toEqual({ status: "unavailable" }));
    expect(getToken()).toBe("token-value");
  });

  it("becomes signed out when the session store reports an expired session", async () => {
    loginMock.mockResolvedValue(SUCCESS);
    const { result } = renderHook(() => useAuthSession());
    await act(async () => {
      await result.current.signIn("asha", "secret");
    });

    act(() => expire());

    expect(result.current.state).toEqual({ status: "signedOut" });
    expect(getToken()).toBeNull();
  });
});
