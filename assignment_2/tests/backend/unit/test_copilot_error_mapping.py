"""SDK failures become typed domain errors; preflight spends no request (FR-14, GR-5)."""

from types import SimpleNamespace

import httpx
import pytest
from app_helpers import create_dict
from copilot._jsonrpc import JsonRpcError
from pydantic import ValidationError

from app.llm import copilot_client
from app.llm.copilot_client import CopilotLLMClient, classify_sdk_error
from app.llm.protocol import LLMRequest
from app.models.action import ProposedActionWire
from app.models.errors import LLMInfrastructureError, LLMOutputError
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-14", "AC-29", "GR-5")


def _rpc(message: str) -> JsonRpcError:
    return JsonRpcError(-32603, message, None)


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (TimeoutError("late"), "timeout"),
        (_rpc("No GitHub OAuth token or Copilot HMAC key provided"), "auth"),
        (_rpc("401 Unauthorized"), "auth"),
        (_rpc("Rate limit exceeded"), "rate_limit"),
        (_rpc("usage limit reached"), "rate_limit"),
        (_rpc("something odd"), "rpc"),
        (RuntimeError("Copilot CLI not found"), "runtime"),
        (OSError("disk"), "runtime"),
        (ConnectionError("reset"), "runtime"),
        (httpx.ConnectError("down"), "runtime"),
    ],
)
def test_sdk_errors_are_classified(error: BaseException, kind: str) -> None:
    mapped = classify_sdk_error(error)
    assert isinstance(mapped, LLMInfrastructureError) and mapped.kind == kind


def test_unlisted_errors_are_not_classified() -> None:
    assert classify_sdk_error(ValueError("our bug")) is None
    assert classify_sdk_error(KeyError("x")) is None


def test_timeout_maps_to_504_and_other_kinds_to_503() -> None:
    assert LLMInfrastructureError("timeout", "x").http_status == 504
    assert LLMInfrastructureError("timeout", "x").code == "llm_timeout"
    assert LLMInfrastructureError("auth", "x").http_status == 503
    assert LLMInfrastructureError("rpc", "x").code == "llm_unavailable"


class _Session:
    def __init__(self, raises: BaseException | None, model: str) -> None:
        self.raises, self.model = raises, model
        self.on_event = None

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def send_and_wait_typed(
        self, prompt: str, response_type: type, *, timeout: float
    ) -> object:
        if self.raises is not None:
            raise self.raises
        usage = SimpleNamespace(
            type=SimpleNamespace(value="assistant.usage"),
            data=SimpleNamespace(model=self.model, input_tokens=1, output_tokens=2),
        )
        assert self.on_event is not None
        self.on_event(usage)
        return response_type.model_validate(create_dict())


class _Client:
    raises: BaseException | None = None
    model = "gpt-6-luna"
    start_raises: BaseException | None = None
    catalog = ("gpt-6-luna", "other")
    authenticated = True
    sessions_created = 0

    def __init__(self, **kwargs: object) -> None:
        self.rpc = SimpleNamespace(models=SimpleNamespace(get_built_in_catalog=self._catalog))

    async def _catalog(self) -> SimpleNamespace:
        return SimpleNamespace(models=[SimpleNamespace(id=i) for i in self.catalog])

    async def start(self) -> None:
        if self.start_raises is not None:
            raise self.start_raises

    async def stop(self) -> None:
        return None

    async def get_auth_status(self) -> SimpleNamespace:
        return SimpleNamespace(isAuthenticated=self.authenticated)

    async def get_status(self) -> SimpleNamespace:
        return SimpleNamespace(version="1.0.105")

    async def create_session(self, **kwargs: object) -> _Session:
        type(self).sessions_created += 1
        session = _Session(self.raises, self.model)
        session.on_event = kwargs["on_event"]  # type: ignore[assignment]  # test double
        return session


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch) -> CopilotLLMClient:
    for name in ("raises", "start_raises"):
        monkeypatch.setattr(_Client, name, None)
    monkeypatch.setattr(_Client, "model", "gpt-6-luna")
    monkeypatch.setattr(_Client, "catalog", ("gpt-6-luna",))
    monkeypatch.setattr(_Client, "authenticated", True)
    monkeypatch.setattr(_Client, "sessions_created", 0)
    monkeypatch.setattr(copilot_client, "CopilotClient", _Client)
    return CopilotLLMClient(Settings(_env_file=None))


def _request() -> LLMRequest:
    return LLMRequest("SYSTEM", "USER", "c1")


@pytest.mark.parametrize(
    ("raised", "kind"),
    [
        (TimeoutError("late"), "timeout"),
        (_rpc("No GitHub OAuth token"), "auth"),
        (RuntimeError("gone"), "runtime"),
    ],
)
async def test_parse_maps_sdk_errors(
    adapter: CopilotLLMClient, monkeypatch: pytest.MonkeyPatch, raised: BaseException, kind: str
) -> None:
    monkeypatch.setattr(_Client, "raises", raised)
    with pytest.raises(LLMInfrastructureError) as info:
        await adapter.parse(_request())
    assert info.value.kind == kind


async def test_invalid_model_output_is_an_output_error_not_infrastructure(
    adapter: CopilotLLMClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    try:
        ProposedActionWire.model_validate({})
    except ValidationError as error:
        monkeypatch.setattr(_Client, "raises", error)
    with pytest.raises(LLMOutputError):
        await adapter.parse(_request())


async def test_an_unlisted_exception_propagates_unchanged(
    adapter: CopilotLLMClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_Client, "raises", ValueError("our bug"))
    with pytest.raises(ValueError, match="our bug"):
        await adapter.parse(_request())


async def test_a_different_served_model_is_model_routing(
    adapter: CopilotLLMClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_Client, "model", "gpt-x")
    with pytest.raises(LLMInfrastructureError) as info:
        await adapter.parse(_request())
    assert info.value.kind == "model_routing"


async def test_preflight_reports_runtime_auth_catalog_and_versions_without_a_request(
    adapter: CopilotLLMClient,
) -> None:
    result = await adapter.preflight()
    assert (result.runtime_ok, result.authenticated, result.model_in_catalog) == (True, True, True)
    assert result.runtime_version == "1.0.105" and result.sdk_version == "1.0.28"
    assert _Client.sessions_created == 0


async def test_preflight_flags_a_missing_model_and_maps_start_failures(
    adapter: CopilotLLMClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_Client, "catalog", ("other",))
    assert (await adapter.preflight()).model_in_catalog is False
    monkeypatch.setattr(_Client, "start_raises", RuntimeError("Copilot CLI not found"))
    fresh = CopilotLLMClient(Settings(_env_file=None))
    with pytest.raises(LLMInfrastructureError) as info:
        await fresh.preflight()
    assert info.value.kind == "runtime"
