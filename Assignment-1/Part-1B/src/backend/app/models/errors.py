"""Typed domain errors; the API maps each to the uniform error body."""

from __future__ import annotations


class DomainError(Exception):
    code = "internal_error"
    http_status = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RequestValidationFailed(DomainError):
    code = "invalid_request"
    http_status = 422


class PayloadTooLarge(DomainError):
    code = "payload_too_large"
    http_status = 413


class LLMOutputError(DomainError):
    """The model answered but its output failed validation (never retried)."""

    code = "model_output_invalid"
    http_status = 502

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__("The model output was not acceptable.")
        self.reason = reason
        self.detail = detail


class LLMInfrastructureError(DomainError):
    """The language-model service failed (auth, timeout, rate limit, runtime, routing)."""

    def __init__(self, kind: str, detail: str = "") -> None:
        timeout = kind == "timeout"
        super().__init__(
            "The language model timed out." if timeout else "The language model is unavailable."
        )
        self.kind = kind
        self.detail = detail
        self.code = "llm_timeout" if timeout else "llm_unavailable"
        self.http_status = 504 if timeout else 503
