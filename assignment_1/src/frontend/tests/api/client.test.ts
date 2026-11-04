import { afterEach, describe, expect, it, vi } from "vitest";
import { request } from "../../src/api/client";
import { ApiError, describeApiError } from "../../src/api/errors";
import { clearToken, getToken, setToken, subscribe } from "../../src/api/session";

function respondWith(status: number, body: string): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue(new Response(body, { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function errorBody(code: string): string {
  return JSON.stringify({ error: { code, message: "details" } });
}

async function failureOf(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) return error;
    throw error;
  }
  throw new Error("expected the request to fail");
}

afterEach(() => {
  vi.unstubAllGlobals();
  clearToken();
});

describe("request", () => {
  it("returns parsed JSON for a 2xx response from the /api/v1 base", async () => {
    const fetchMock = respondWith(200, JSON.stringify({ items: [1, 2] }));

    const result = await request<{ items: number[] }>("/buses");

    expect(result).toEqual({ items: [1, 2] });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/buses", expect.objectContaining({}));
  });

  it("sends a JSON body with the content type for POST requests", async () => {
    const fetchMock = respondWith(201, JSON.stringify({ bookings: [] }));

    await request("/bookings", { method: "POST", body: { bus_id: 1 } });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ bus_id: 1 }));
    expect(new Headers(init.headers).get("content-type")).toBe("application/json");
  });

  it("maps 409 seat_unavailable to a conflict error", async () => {
    respondWith(409, errorBody("seat_unavailable"));

    const error = await failureOf(request("/bookings"));

    expect(error.kind).toBe("conflict");
    expect(error.status).toBe(409);
    expect(error.code).toBe("seat_unavailable");
  });

  it.each([400, 404, 422])("maps %i to an invalid error", async (status) => {
    respondWith(status, errorBody("some_code"));

    const error = await failureOf(request("/bookings"));

    expect(error.kind).toBe("invalid");
  });

  it.each([500, 503])("maps %i to an unavailable error", async (status) => {
    respondWith(status, errorBody("service_unavailable"));

    const error = await failureOf(request("/buses"));

    expect(error.kind).toBe("unavailable");
  });

  it("maps a network failure to an unavailable error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await failureOf(request("/buses"));

    expect(error.kind).toBe("unavailable");
  });

  it("maps a non-JSON error body to an unavailable error", async () => {
    respondWith(400, "<html>bad gateway</html>");

    const error = await failureOf(request("/buses"));

    expect(error.kind).toBe("unavailable");
  });

  it("sends the bearer token when a session exists", async () => {
    setToken("token-value");
    const fetchMock = respondWith(200, "{}");

    await request("/buses");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer token-value");
  });

  it("sends no authorization header without a session", async () => {
    const fetchMock = respondWith(200, "{}");

    await request("/auth/login", { method: "POST", body: {} });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).has("authorization")).toBe(false);
  });

  it("maps 401 invalid_credentials to a credentials error", async () => {
    respondWith(401, errorBody("invalid_credentials"));

    const error = await failureOf(request("/auth/login", { method: "POST", body: {} }));

    expect(error.kind).toBe("credentials");
    expect(error.status).toBe(401);
  });

  it("maps 401 unauthenticated to its own kind", async () => {
    respondWith(401, errorBody("unauthenticated"));

    const error = await failureOf(request("/buses"));

    expect(error.kind).toBe("unauthenticated");
  });

  it("maps 429 to a throttled error", async () => {
    respondWith(429, errorBody("too_many_attempts"));

    const error = await failureOf(request("/auth/login", { method: "POST", body: {} }));

    expect(error.kind).toBe("throttled");
  });

  it("ends the session when a protected call returns 401 unauthenticated", async () => {
    setToken("token-value");
    const listener = vi.fn();
    const unsubscribe = subscribe(listener);
    respondWith(401, errorBody("unauthenticated"));

    await failureOf(request("/buses"));

    expect(getToken()).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it("reports no expiry for a 401 when the token was already cleared by a sign-out", async () => {
    setToken("token-value");
    const listener = vi.fn();
    const unsubscribe = subscribe(listener);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() => {
        clearToken();
        return Promise.resolve(new Response(errorBody("unauthenticated"), { status: 401 }));
      }),
    );

    await failureOf(request("/buses"));

    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("does not end the session for a refused sign-in", async () => {
    setToken("token-value");
    const listener = vi.fn();
    const unsubscribe = subscribe(listener);
    respondWith(401, errorBody("invalid_credentials"));

    await failureOf(request("/auth/login", { method: "POST", body: {} }));

    expect(getToken()).toBe("token-value");
    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });

  it.each([503, 500])("keeps the session when a protected call fails with %i", async (status) => {
    setToken("token-value");
    respondWith(status, errorBody("service_unavailable"));

    await failureOf(request("/buses"));

    expect(getToken()).toBe("token-value");
  });

  it("keeps the session when the network fails", async () => {
    setToken("token-value");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await failureOf(request("/buses"));

    expect(getToken()).toBe("token-value");
  });
});

describe("describeApiError", () => {
  it.each([
    ["conflict", "Seat no longer available"],
    ["invalid", "Invalid request"],
    ["unavailable", "Service unavailable"],
  ] as const)("describes a %s error", (kind, text) => {
    expect(describeApiError(new ApiError(kind, 0, "code", "message"))).toContain(text);
  });

  it("describes a credentials error without saying which part was wrong", () => {
    const message = describeApiError(new ApiError("credentials", 401, "invalid_credentials", "x"));

    expect(message).toBe("Invalid username or password");
  });

  it("shows the server message for a throttled error", () => {
    const server = "Too many failed sign-in attempts. Try again in 7 seconds.";

    expect(describeApiError(new ApiError("throttled", 429, "too_many_attempts", server))).toBe(
      server,
    );
  });

  it("describes an unknown error as service unavailable", () => {
    expect(describeApiError(new Error("boom"))).toContain("Service unavailable");
  });
});
