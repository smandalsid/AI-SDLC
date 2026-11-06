"""The harness executor runs each case through the real HTTP application (FR-14, FR-15, AC-29)."""

import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from app_helpers import JsonObject, action_dict, create_dict

from app.eval_adapter import AppExecutor, build
from app.llm.copilot_client import CopilotLLMClient
from app.llm.protocol import CallRecord, LLMRequest, LLMResult, PreflightResult
from app.llm.stub_client import Scripted, StubLLMClient
from app.models.action import ProposedActionWire
from app.models.errors import LLMInfrastructureError
from app.services.prompt_builder import CANARY_PHRASE
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-14", "FR-15", "AC-15", "AC-29", "GR-5", "GR-4")

SETTINGS = Settings(_env_file=None)
SENTINEL_VALUE = "not-a-real-token-for-tests"


def _case(
    case_id: str = "N01", text: object = "remind me to pay rent", **inputs: object
) -> JsonObject:
    body = {"text": text, "timezone": "UTC", "now": "2026-11-05T10:00:00+00:00", "reminders": []}
    return {"id": case_id, "category": "normal", "input": {**body, **inputs}}


class LiveLikeClient:
    """Stands in for the SDK client: reports a served model and a preflight result."""

    def __init__(self, served: str | None, preflight: PreflightResult | BaseException) -> None:
        self.served, self.outcome = served, preflight
        self.requests: list[LLMRequest] = []

    async def parse(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        wire = ProposedActionWire.model_validate(create_dict())
        return LLMResult(wire, CallRecord("gpt-6-luna", self.served, "low", 10, 5, 7, 1))

    async def preflight(self) -> PreflightResult:
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def _ok_preflight(
    runtime_ok: bool = True, authenticated: bool = True, model_in_catalog: bool = True
) -> PreflightResult:
    return PreflightResult(
        runtime_ok=runtime_ok,
        authenticated=authenticated,
        model_in_catalog=model_in_catalog,
        runtime_version="1.0.105",
        sdk_version="1.0.28",
    )


@pytest.fixture
def executors() -> Iterator[list[AppExecutor]]:
    made: list[AppExecutor] = []
    yield made
    for executor in made:
        executor.close()


def _stub(executors: list[AppExecutor], *responses: Scripted) -> tuple[AppExecutor, StubLLMClient]:
    stub = StubLLMClient(*responses)
    executor = build(mode="replay", recordings_dir=None, settings=SETTINGS, llm=stub)
    executors.append(executor)
    return executor, stub


def test_a_200_case_is_scored_with_the_action_and_the_applied_result(
    executors: list[AppExecutor],
) -> None:
    executor, stub = _stub(executors, create_dict())
    obs = executor.execute(_case(), 1)
    assert obs.status_code == 200 and obs.infra_kind is None and obs.model_calls == 1
    assert obs.action is not None and obs.applied is not None
    assert obs.action["intent"] == "create" and obs.applied["operation"] == "created"
    assert obs.applied["reminders"][0]["title"] == "pay rent"
    assert stub.requests[0].correlation_id == "N01.1"


def test_supplied_reminders_and_the_run_index_reach_the_application(
    executors: list[AppExecutor],
) -> None:
    reminders = [{"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}]
    executor, stub = _stub(executors, action_dict())
    obs = executor.execute(_case("N07", reminders=reminders), 3)
    assert obs.applied is not None and obs.applied["reminders"] == reminders
    assert stub.requests[0].correlation_id == "N07.3"


def test_ac_14_a_too_long_refusal_is_a_200_with_no_model_call(executors: list[AppExecutor]) -> None:
    executor, stub = _stub(executors, create_dict())
    obs = executor.execute(_case("X01", text="x" * 1001), 1)
    assert obs.status_code == 200 and obs.model_calls == 0 and stub.calls == 0
    assert obs.action is not None and obs.action["refusal_reason"] == "too_long"
    assert obs.call is None


@pytest.mark.parametrize("text", ["", "   ", 12345, None, ["a"]], ids=repr)
def test_ac_15_empty_or_non_text_is_a_422_without_an_action(
    executors: list[AppExecutor], text: object
) -> None:
    executor, stub = _stub(executors, create_dict())
    obs = executor.execute(_case("X02", text=text), 1)
    assert obs.status_code == 422 and obs.action is None and obs.applied is None
    assert obs.model_calls == 0 and obs.infra_kind is None and stub.calls == 0


def test_a_413_is_reported_with_its_status_and_no_action(executors: list[AppExecutor]) -> None:
    executor, _ = _stub(executors, create_dict())
    big = _case("X05", text="x" * 2_000_000)
    obs = executor.execute(big, 1)
    assert obs.status_code == 413 and obs.action is None and obs.model_calls == 0


def test_a_502_is_a_failed_case_not_infrastructure(executors: list[AppExecutor]) -> None:
    executor, _ = _stub(executors, {**create_dict(), "extra": "field"})
    obs = executor.execute(_case(), 1)
    assert obs.status_code == 502 and obs.action is None and obs.applied is None
    assert obs.infra_kind is None and obs.model_calls == 1


@pytest.mark.parametrize(
    ("kind", "status"),
    [
        ("auth", 503),
        ("rate_limit", 503),
        ("runtime", 503),
        ("timeout", 504),
        ("model_routing", 503),
    ],
)
def test_service_failures_are_infrastructure_with_their_kind(
    executors: list[AppExecutor], kind: str, status: int
) -> None:
    executor, _ = _stub(executors, LLMInfrastructureError(kind, "boom"))
    obs = executor.execute(_case(), 1)
    assert obs.status_code == status and obs.infra_kind == kind and obs.action is None


def test_a_served_model_other_than_the_configured_one_is_model_routing() -> None:
    client = LiveLikeClient("some-other-model", _ok_preflight())
    executor = build(mode="live", recordings_dir=None, settings=SETTINGS, llm=client)
    try:
        obs = executor.execute(_case(), 1)
    finally:
        executor.close()
    assert obs.status_code == 200 and obs.infra_kind == "model_routing"
    assert obs.call is not None and obs.call["model_served"] == "some-other-model"


def test_the_configured_model_is_recorded_as_served_in_a_live_run() -> None:
    client = LiveLikeClient(SETTINGS.model_id, _ok_preflight())
    executor = build(mode="live", recordings_dir=None, settings=SETTINGS, llm=client)
    try:
        obs = executor.execute(_case(), 1)
    finally:
        executor.close()
    assert obs.infra_kind is None and obs.call is not None
    assert obs.call["model_served"] == SETTINGS.model_id and obs.call["input_tokens"] == 10
    assert obs.call["reasoning_effort"] == "low" and obs.call["duration_ms"] == 7


def test_replay_and_stub_runs_never_claim_a_served_model(executors: list[AppExecutor]) -> None:
    executor, _ = _stub(executors, create_dict())
    obs = executor.execute(_case(), 1)
    assert obs.call is not None and obs.call["model_served"] is None


def test_replay_reads_the_recording_for_the_case_and_run(tmp_path: Path) -> None:
    (tmp_path / "N01.2.json").write_text(json.dumps(create_dict()))
    executor = build(mode="replay", recordings_dir=tmp_path, settings=SETTINGS)
    try:
        replayed = executor.execute(_case(), 2)
        assert replayed.action is not None and replayed.action["intent"] == "create"
        missing = executor.execute(_case(), 1)
    finally:
        executor.close()
    assert missing.status_code == 503 and missing.infra_kind == "replay_missing"


def test_a_leaking_output_is_a_502_through_the_wired_sentinels(
    executors: list[AppExecutor],
) -> None:
    executor, _ = _stub(executors, action_dict(clarification_question=f"it is {CANARY_PHRASE}"))
    obs = executor.execute(_case(), 1)
    assert obs.status_code == 502 and obs.action is None


def test_sentinels_are_the_prompt_canary_and_the_configured_secrets() -> None:
    settings = Settings(_env_file=None, gh_token=SENTINEL_VALUE)
    executor = build(mode="replay", recordings_dir=None, settings=settings, llm=StubLLMClient())
    try:
        assert executor.sentinels() == [CANARY_PHRASE, SENTINEL_VALUE]
    finally:
        executor.close()


def test_metadata_names_the_model_effort_and_sdk(executors: list[AppExecutor]) -> None:
    executor, _ = _stub(executors, create_dict())
    meta = executor.metadata()
    assert meta["model_requested"] == SETTINGS.model_id
    assert meta["reasoning_effort"] == SETTINGS.reasoning_effort and meta["sdk_version"]


def test_preflight_passes_with_the_runtime_version_recorded() -> None:
    client = LiveLikeClient(None, _ok_preflight())
    executor = build(mode="live", recordings_dir=None, settings=SETTINGS, llm=client)
    try:
        report = executor.preflight()
        assert report.ok and report.cause == ""
        assert report.info["runtime_version"] == "1.0.105"
        assert executor.metadata()["runtime_version"] == "1.0.105"
    finally:
        executor.close()


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (_ok_preflight(authenticated=False), "not authenticated"),
        (_ok_preflight(model_in_catalog=False), "not in the catalog"),
        (_ok_preflight(runtime_ok=False), "runtime"),
        (LLMInfrastructureError("runtime", "download failed"), "runtime"),
    ],
    ids=["auth", "catalog", "runtime-flag", "runtime-error"],
)
def test_a_failed_preflight_reports_the_cause(
    outcome: PreflightResult | BaseException, expected: str
) -> None:
    executor = build(
        mode="live", recordings_dir=None, settings=SETTINGS, llm=LiveLikeClient(None, outcome)
    )
    try:
        report = executor.preflight()
    finally:
        executor.close()
    assert not report.ok and expected in report.cause


def test_a_client_without_preflight_support_passes_it() -> None:
    executor = build(mode="replay", recordings_dir=None, settings=SETTINGS, llm=StubLLMClient())
    try:
        assert executor.preflight().ok
    finally:
        executor.close()


def test_live_mode_wires_the_copilot_client_without_starting_it() -> None:
    executor = build(mode="live", recordings_dir=None, settings=SETTINGS)
    try:
        assert isinstance(executor.llm, CopilotLLMClient)
    finally:
        executor.close()


def test_cases_run_concurrently_from_several_threads(executors: list[AppExecutor]) -> None:
    executor, stub = _stub(executors, create_dict())
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda i: executor.execute(_case(), i), range(1, 13)))
    assert all(r.status_code == 200 for r in results) and stub.calls == 12
    assert sorted(req.correlation_id for req in stub.requests) == sorted(
        f"N01.{i}" for i in range(1, 13)
    )
