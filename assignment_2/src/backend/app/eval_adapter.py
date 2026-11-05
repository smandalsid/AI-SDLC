"""Evaluation executor: runs each case through the real HTTP application (FR-14, FR-15).

The harness imports `build` through `--executor-factory app.eval_adapter:build`; nothing in the
application imports this module.
"""

from __future__ import annotations

import asyncio
import atexit
import importlib.metadata
import threading
from collections.abc import Coroutine
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, TypeVar, cast

import httpx
from fastapi import FastAPI

from app.api.main import create_app
from app.llm.copilot_client import CopilotLLMClient
from app.llm.protocol import CallRecord, LLMClient, LLMRequest, LLMResult, PreflightResult
from app.llm.replay_client import ReplayLLMClient
from app.models.errors import LLMInfrastructureError
from app.services.leak_guard import sentinels_from
from app.services.prompt_builder import load_template
from app.settings import Settings
from eval_runner import PreflightReport
from evaluators.common import JSON, Observation

T = TypeVar("T")
DEFAULT_RECORDINGS = Path("evals/recorded")
INFRA_STATUSES = (503, 504)
Payload = dict[str, Any]  # parsed JSON has no static type


class _LoopThread:
    """One event loop for every request, so the SDK client lives on a single loop."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def run(self, coroutine: Coroutine[object, object, T]) -> T:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result()

    def close(self) -> None:
        if self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.close()


class _Recorder:
    """Wraps the shared client for one case run: counts calls, keeps the record or the fault."""

    def __init__(self, inner: LLMClient, correlation_id: str) -> None:
        self._inner, self._correlation_id = inner, correlation_id
        self.calls = 0
        self.record: CallRecord | None = None
        self.fault: LLMInfrastructureError | None = None

    async def parse(self, request: LLMRequest) -> LLMResult:
        self.calls += 1
        try:
            result = await self._inner.parse(replace(request, correlation_id=self._correlation_id))
        except LLMInfrastructureError as error:
            self.fault = error
            raise
        self.record = result.record
        return result


def _request_body(case: JSON) -> Payload:
    keys = ("text", "timezone", "now", "reminders")
    return {key: case["input"][key] for key in keys if key in case["input"]}


async def _post(app: FastAPI, body: Payload) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://eval") as client:
        return await client.post("/api/v1/actions", json=body)


def _payload(response: httpx.Response) -> Payload:
    try:
        parsed = response.json()
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class AppExecutor:
    """The harness `CaseExecutor` over the application."""

    def __init__(self, settings: Settings, llm: LLMClient, *, live: bool) -> None:
        self._settings, self._live = settings, live
        self.llm = llm
        self._loop = _LoopThread()
        self._runtime_version: str | None = None
        self._closed = False

    def execute(self, case: JSON, run_index: int) -> Observation:
        recorder = _Recorder(self.llm, f"{case['id']}.{run_index}")
        app = create_app(settings=self._settings, llm_client=recorder)
        response = self._loop.run(_post(app, _request_body(case)))
        return self._observe(response, recorder)

    def _observe(self, response: httpx.Response, recorder: _Recorder) -> Observation:
        status, payload = response.status_code, _payload(response)
        ok = status == 200
        return Observation(
            status_code=status,
            action=payload.get("action") if ok else None,
            applied=payload.get("applied") if ok else None,
            model_calls=recorder.calls,
            infra_kind=self._infra_kind(status, payload, recorder),
            call=self._call(recorder.record),
        )

    def _infra_kind(self, status: int, payload: Payload, recorder: _Recorder) -> str | None:
        if status in INFRA_STATUSES:
            if recorder.fault is not None:
                return recorder.fault.kind
            return str(payload.get("error", {}).get("code", "llm_unavailable"))
        served = recorder.record.model_served if recorder.record else None
        if self._live and served not in (None, self._settings.model_id):
            return "model_routing"
        return None

    def _call(self, record: CallRecord | None) -> JSON | None:
        if record is None:
            return None
        call = asdict(record)
        if not self._live:
            call["model_served"] = None
        return call

    def preflight(self) -> PreflightReport:
        probe = getattr(self.llm, "preflight", None)
        if probe is None:
            return PreflightReport(True, "", {})
        try:
            result = cast("PreflightResult", self._loop.run(probe()))
        except LLMInfrastructureError as error:
            return PreflightReport(False, f"{error.kind}: {error.detail}", {})
        self._runtime_version = result.runtime_version
        info = {"runtime_version": result.runtime_version, "sdk_version": result.sdk_version}
        return PreflightReport(not self._problem(result), self._problem(result), info)

    def _problem(self, result: PreflightResult) -> str:
        if not result.runtime_ok:
            return "the SDK runtime is not available"
        if not result.authenticated:
            return "the SDK is not authenticated"
        if not result.model_in_catalog:
            return f"model {self._settings.model_id} is not in the catalog"
        return ""

    def sentinels(self) -> list[str]:
        return sentinels_from(load_template(), self._settings.secret_values())

    def metadata(self) -> dict[str, str]:
        meta = {
            "model_requested": self._settings.model_id,
            "reasoning_effort": self._settings.reasoning_effort,
            "sdk_version": importlib.metadata.version("github-copilot-sdk"),
        }
        if self._runtime_version is not None:
            meta["runtime_version"] = self._runtime_version
        return meta

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if isinstance(self.llm, CopilotLLMClient):
            self._loop.run(self.llm.stop())
        self._loop.close()


def build(
    mode: str,
    recordings_dir: Path | None,
    *,
    settings: Settings | None = None,
    llm: LLMClient | None = None,
) -> AppExecutor:
    """The harness factory: `live` talks to the SDK, `replay` reads recorded outputs."""
    settings = Settings() if settings is None else settings
    live = mode == "live"
    client: LLMClient
    if llm is not None:
        client = llm
    elif live:
        client = CopilotLLMClient(settings)
    else:
        client = ReplayLLMClient(recordings_dir or DEFAULT_RECORDINGS)
    executor = AppExecutor(settings, client, live=live)
    if live and llm is None:
        atexit.register(executor.close)
    return executor
