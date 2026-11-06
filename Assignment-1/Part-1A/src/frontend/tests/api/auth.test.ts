import { afterEach, describe, expect, it, vi } from "vitest";
import { login, logout, me } from "../../src/api/auth";
import { clearToken, setToken } from "../../src/api/session";

afterEach(() => {
  vi.unstubAllGlobals();
  clearToken();
});

const RESPONSE = {
  access_token: "token-value",
  token_type: "bearer",
  expires_at: "2026-01-15T11:00:00Z",
  user: { id: 1, name: "Asha" },
};

describe("login", () => {
  it("posts exactly the username and password to /auth/login and returns the response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(RESPONSE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await login("asha", "pass word");

    expect(result).toEqual(RESPONSE);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/login");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ username: "asha", password: "pass word" }));
  });

  it("keeps the credentials out of the URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(RESPONSE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await login("asha", "pass word");

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).not.toMatch(/asha|pass/);
  });
});

describe("me", () => {
  it("gets /auth/me with the bearer token and returns the user", async () => {
    setToken("token-value");
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: 1, name: "Asha" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const user = await me();

    expect(user).toEqual({ id: 1, name: "Asha" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/me");
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer token-value");
  });
});

describe("logout", () => {
  it("posts to /auth/logout with the bearer token and accepts the empty 204 answer", async () => {
    setToken("token-value");
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(logout()).resolves.toBeUndefined();

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/logout");
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer token-value");
  });

  it("rejects when the server answers 401", async () => {
    setToken("token-value");
    const body = { error: { code: "unauthenticated", message: "Authentication required." } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 401 })));

    await expect(logout()).rejects.toMatchObject({ status: 401 });
  });
});
