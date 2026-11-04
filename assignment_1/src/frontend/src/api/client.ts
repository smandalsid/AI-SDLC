import { ApiError, kindForStatus } from "./errors";
import { getToken } from "./session";
import type { ErrorResponse } from "./types";

const configuredBase: unknown = import.meta.env.VITE_API_BASE_URL;
const BASE_URL = typeof configuredBase === "string" && configuredBase ? configuredBase : "/api/v1";

export interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string"
  );
}

async function toApiError(response: Response): Promise<ApiError> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(await response.text());
  } catch {
    parsed = undefined;
  }
  if (!isErrorResponse(parsed)) {
    return new ApiError("unavailable", response.status, "unexpected_response", "Unexpected response");
  }
  const { code, message } = parsed.error;
  return new ApiError(kindForStatus(response.status, code), response.status, code, message);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = getToken();
  if (token !== null) headers.Authorization = `Bearer ${token}`;
  const init: RequestInit = { method: options.method ?? "GET", headers };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError("unavailable", 0, "network_error", "The service could not be reached");
  }
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}
