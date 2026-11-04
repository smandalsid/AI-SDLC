export type ApiErrorKind =
  | "conflict"
  | "invalid"
  | "unavailable"
  | "credentials"
  | "throttled"
  | "unauthenticated";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  readonly code: string;

  constructor(kind: ApiErrorKind, status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.code = code;
  }
}

export function kindForStatus(status: number, code: string): ApiErrorKind {
  if (status === 401) return code === "unauthenticated" ? "unauthenticated" : "credentials";
  if (status === 429) return "throttled";
  if (status === 409) return "conflict";
  if (status === 400 || status === 404 || status === 422) return "invalid";
  return "unavailable";
}

const MESSAGES: Record<ApiErrorKind, string> = {
  conflict: "Seat no longer available. The seat list has been refreshed.",
  invalid: "Invalid request. Please check your selection and try again.",
  unavailable: "Service unavailable. Please try again in a moment.",
  credentials: "Invalid username or password",
  throttled: "Too many failed sign-in attempts. Please wait a moment and try again.",
  unauthenticated: "Please sign in to continue.",
};

export function describeApiError(error: unknown): string {
  if (!(error instanceof ApiError)) return MESSAGES.unavailable;
  // The server message states how many seconds to wait.
  return error.kind === "throttled" ? error.message : MESSAGES[error.kind];
}
