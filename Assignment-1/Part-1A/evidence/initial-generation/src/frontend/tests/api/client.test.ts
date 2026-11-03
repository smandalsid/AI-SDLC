import { afterEach, describe, expect, it, vi } from "vitest";
import { request } from "../../src/api/client";
import { ApiError, describeApiError } from "../../src/api/errors";

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
});

describe("describeApiError", () => {
  it.each([
    ["conflict", "Seat no longer available"],
    ["invalid", "Invalid request"],
    ["unavailable", "Service unavailable"],
  ] as const)("describes a %s error", (kind, text) => {
    expect(describeApiError(new ApiError(kind, 0, "code", "message"))).toContain(text);
  });

  it("describes an unknown error as service unavailable", () => {
    expect(describeApiError(new Error("boom"))).toContain("Service unavailable");
  });
});
