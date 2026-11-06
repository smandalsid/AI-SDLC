"""The only module that talks to the Copilot SDK (constitution: one SDK module, least privilege)."""

from __future__ import annotations

import importlib.metadata
import tempfile
import time

import httpx
from copilot import CopilotClient
from copilot._jsonrpc import JsonRpcError
from copilot.rpc import PermissionDecisionReject
from pydantic import ValidationError

from app.llm.protocol import CallRecord, LLMRequest, LLMResult, PreflightResult
from app.models.action import ProposedActionWire
from app.models.errors import LLMInfrastructureError, LLMOutputError
from app.settings import Settings

AUTH_PATTERNS = ("oauth token", "hmac", "401", "unauthor", "forbidden")
RATE_PATTERNS = ("rate limit", "quota", "usage limit", "429")
SDK_ERRORS = (TimeoutError, JsonRpcError, RuntimeError, OSError, httpx.HTTPError)
USAGE_EVENT = "assistant.usage"


def _rpc_kind(message: str) -> str:
    if any(p in message for p in AUTH_PATTERNS):
        return "auth"
    if any(p in message for p in RATE_PATTERNS):
        return "rate_limit"
    return "rpc"


def classify_sdk_error(error: BaseException) -> LLMInfrastructureError | None:
    """Map an SDK or runtime failure to a typed domain error; None when it is not infrastructure."""
    if isinstance(error, TimeoutError):
        kind = "timeout"
    elif isinstance(error, JsonRpcError):
        kind = _rpc_kind(f"{error} {getattr(error, 'message', '')}".lower())
    elif isinstance(error, SDK_ERRORS):
        kind = "runtime"
    else:
        return None
    return LLMInfrastructureError(kind, f"{type(error).__name__}: {error}")


def _reject_all(*_: object) -> PermissionDecisionReject:
    return PermissionDecisionReject(feedback="Tools and permissions are not available.")


class _Usage:
    """Captures the served model and token counts from the assistant.usage event."""

    def __init__(self) -> None:
        self.model: str | None = None
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None

    def on_event(self, event: object) -> None:
        kind = getattr(getattr(event, "type", None), "value", None)
        data = getattr(event, "data", None)
        if kind == USAGE_EVENT and data is not None:
            self.model = getattr(data, "model", None)
            self.input_tokens = getattr(data, "input_tokens", None)
            self.output_tokens = getattr(data, "output_tokens", None)


def _raise_mapped(error: BaseException) -> LLMInfrastructureError:
    mapped = classify_sdk_error(error)
    if mapped is None:
        raise error
    return mapped


class CopilotLLMClient:
    """One CopilotClient per process; one fresh session and empty working directory per request."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: CopilotClient | None = None
        self._base: tempfile.TemporaryDirectory[str] | None = None

    async def start(self) -> None:
        if self._client is not None:
            return
        token = self._settings.token_value()
        base = tempfile.TemporaryDirectory(prefix="reminder-sdk-")
        client = CopilotClient(
            mode="empty",
            base_directory=base.name,
            working_directory=base.name,
            github_token=token,
            use_logged_in_user=None if token is None else False,
        )
        try:
            await client.start()
        except SDK_ERRORS as error:
            base.cleanup()
            raise _raise_mapped(error) from error
        self._client, self._base = client, base

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.stop()
        if self._base is not None:
            self._base.cleanup()
        self._client, self._base = None, None

    async def _started(self) -> CopilotClient:
        await self.start()
        assert self._client is not None  # noqa: S101  # start() sets it or raises
        return self._client

    async def parse(self, request: LLMRequest) -> LLMResult:
        client = await self._started()
        usage, began = _Usage(), time.monotonic()
        with tempfile.TemporaryDirectory(prefix="reminder-session-") as workdir:
            try:
                session = await client.create_session(
                    on_permission_request=_reject_all,
                    model=self._settings.model_id,
                    reasoning_effort=self._settings.reasoning_effort,
                    available_tools=[],
                    infinite_sessions={"enabled": False},
                    memory={"enabled": False},
                    working_directory=workdir,
                    system_message={"mode": "replace", "content": request.system_prompt},
                    on_event=usage.on_event,
                )
                async with session:
                    wire = await session.send_and_wait_typed(
                        request.user_message,
                        ProposedActionWire,
                        timeout=float(self._settings.sdk_timeout_seconds),
                    )
            except ValidationError as error:
                raise LLMOutputError("schema", str(error)) from error
            except SDK_ERRORS as error:
                raise _raise_mapped(error) from error
        return self._result(wire, usage, began)

    def _result(self, wire: ProposedActionWire, usage: _Usage, began: float) -> LLMResult:
        if usage.model is not None and usage.model != self._settings.model_id:
            raise LLMInfrastructureError(
                "model_routing", f"served {usage.model}, expected {self._settings.model_id}"
            )
        record = CallRecord(
            model_requested=self._settings.model_id,
            model_served=usage.model,
            reasoning_effort=self._settings.reasoning_effort,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration_ms=int((time.monotonic() - began) * 1000),
            attempt=1,
        )
        return LLMResult(wire, record)

    async def preflight(self) -> PreflightResult:
        client = await self._started()
        try:
            auth = await client.get_auth_status()
            catalog = await client.rpc.models.get_built_in_catalog()
            status = await client.get_status()
        except SDK_ERRORS as error:
            raise _raise_mapped(error) from error
        return PreflightResult(
            runtime_ok=True,
            authenticated=bool(auth.isAuthenticated),
            model_in_catalog=any(m.id == self._settings.model_id for m in catalog.models),
            runtime_version=str(status.version),
            sdk_version=importlib.metadata.version("github-copilot-sdk"),
        )
