export type ApiErrorKind = "conflict" | "invalid" | "unavailable";

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

export function kindForStatus(status: number): ApiErrorKind {
  if (status === 409) return "conflict";
  if (status === 400 || status === 404 || status === 422) return "invalid";
  return "unavailable";
}

const MESSAGES: Record<ApiErrorKind, string> = {
  conflict: "Seat no longer available. The seat list has been refreshed.",
  invalid: "Invalid request. Please check your selection and try again.",
  unavailable: "Service unavailable. Please try again in a moment.",
};

export function describeApiError(error: unknown): string {
  return error instanceof ApiError ? MESSAGES[error.kind] : MESSAGES.unavailable;
}
