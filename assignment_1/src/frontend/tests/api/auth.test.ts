import { afterEach, describe, expect, it, vi } from "vitest";
import { login } from "../../src/api/auth";

afterEach(() => {
  vi.unstubAllGlobals();
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
