"""The SDK adapter is least-privilege and matches the installed SDK (Principle VIII)."""

import inspect
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import copilot
import pytest
from app_helpers import create_dict
from copilot.rpc import PermissionDecisionReject

from app.llm import copilot_client
from app.llm.copilot_client import CopilotLLMClient
from app.llm.protocol import LLMRequest
from app.models.action import ProposedActionWire
from app.settings import Settings

pytestmark = pytest.mark.covers("GR-5", "FR-14")

USAGE = SimpleNamespace(
    type=SimpleNamespace(value="assistant.usage"),
    data=SimpleNamespace(model="gpt-6-luna", input_tokens=10, output_tokens=5),
)


class FakeSession:
    def __init__(self, kwargs: dict[str, object], owner: "FakeClient") -> None:
        self.kwargs, self.owner, self.closed = kwargs, owner, False
        self.listing_at_start = sorted(
            p.name for p in Path(str(kwargs["working_directory"])).iterdir()
        )

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.closed = True

    async def send_and_wait_typed(
        self, prompt: str, response_type: type[ProposedActionWire], *, timeout: float
    ) -> ProposedActionWire:
        self.owner.sent.append((prompt, response_type, timeout))
        on_event = self.kwargs["on_event"]
        assert callable(on_event)
        on_event(USAGE)
        return response_type.model_validate(create_dict())


class FakeClient:
    instances: ClassVar[list["FakeClient"]] = []

    def __init__(self, **kwargs: object) -> None:
        self.init_kwargs = kwargs
        self.sessions: list[FakeSession] = []
        self.sent: list[tuple[str, type[ProposedActionWire], float]] = []
        FakeClient.instances.append(self)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def create_session(self, **kwargs: object) -> FakeSession:
        session = FakeSession(kwargs, self)
        self.sessions.append(session)
        return session


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch) -> CopilotLLMClient:
    FakeClient.instances = []
    monkeypatch.setattr(copilot_client, "CopilotClient", FakeClient)
    return CopilotLLMClient(Settings(_env_file=None))


def _request() -> LLMRequest:
    return LLMRequest(system_prompt="SYSTEM", user_message="USER", correlation_id="c1")


async def test_client_and_session_are_created_least_privilege(adapter: CopilotLLMClient) -> None:
    result = await adapter.parse(_request())
    client = FakeClient.instances[0]
    assert client.init_kwargs["mode"] == "empty"
    assert Path(str(client.init_kwargs["base_directory"])).is_dir()
    kwargs = client.sessions[0].kwargs
    assert kwargs["available_tools"] == []
    assert kwargs["infinite_sessions"] == {"enabled": False}
    assert kwargs["memory"] == {"enabled": False}
    assert kwargs["model"] == "gpt-6-luna" and kwargs["reasoning_effort"] == "low"
    assert kwargs["system_message"] == {"mode": "replace", "content": "SYSTEM"}
    assert client.sessions[0].listing_at_start == []
    assert result.record.model_served == "gpt-6-luna"


async def test_every_permission_request_is_rejected(adapter: CopilotLLMClient) -> None:
    await adapter.parse(_request())
    handler = FakeClient.instances[0].sessions[0].kwargs["on_permission_request"]
    assert callable(handler)
    decision = handler(object(), {})
    assert isinstance(decision, PermissionDecisionReject)


async def test_structured_output_uses_the_wire_model_and_the_configured_timeout(
    adapter: CopilotLLMClient,
) -> None:
    await adapter.parse(_request())
    prompt, response_type, timeout = FakeClient.instances[0].sent[0]
    assert (prompt, response_type, timeout) == ("USER", ProposedActionWire, 60)


async def test_each_request_gets_a_fresh_session_that_is_closed(adapter: CopilotLLMClient) -> None:
    await adapter.parse(_request())
    await adapter.parse(_request())
    sessions = FakeClient.instances[0].sessions
    assert len(FakeClient.instances) == 1 and len(sessions) == 2
    assert all(s.closed for s in sessions)
    dirs = {str(s.kwargs["working_directory"]) for s in sessions}
    assert len(dirs) == 2


def test_the_keyword_names_exist_in_the_installed_sdk() -> None:
    create = set(inspect.signature(copilot.CopilotClient.create_session).parameters)
    assert {
        "on_permission_request",
        "model",
        "reasoning_effort",
        "available_tools",
        "infinite_sessions",
        "memory",
        "working_directory",
        "system_message",
        "on_event",
    } <= create
    init = set(inspect.signature(copilot.CopilotClient.__init__).parameters)
    assert {"mode", "base_directory", "working_directory"} <= init
    from copilot.session import CopilotSession

    assert "timeout" in inspect.signature(CopilotSession.send_and_wait_typed).parameters
    assert "feedback" in inspect.signature(PermissionDecisionReject.__init__).parameters
    assert tempfile.gettempdir()
