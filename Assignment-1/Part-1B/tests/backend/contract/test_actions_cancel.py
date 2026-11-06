"""POST /api/v1/actions for cancel: exactly one reminder is removed (FR-7)."""

import httpx
import pytest
from app_helpers import FixedClock, JsonObject, action_dict
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.llm.stub_client import Scripted, StubLLMClient
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-7", "INV-5", "GR-5", "AC-22", "AC-23")

NOW = "2026-11-05T10:00:00+00:00"
R1 = {"id": "r1", "title": "Dentist appointment", "time": "2026-11-06T10:00:00+00:00"}
R2 = {"id": "r2", "title": "Gym session", "time": "2026-11-07T07:00:00+00:00"}


def _post(scripted: Scripted, text: str) -> httpx.Response:
    app = create_app(
        settings=Settings(_env_file=None), llm_client=StubLLMClient(scripted), clock=FixedClock()
    )
    response: httpx.Response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/actions", json={"text": text, "now": NOW, "reminders": [R1, R2]}
    )
    return response


def _cancel(target: str) -> dict[str, object]:
    return action_dict(intent="cancel", target_reminder_id=target, clarification_question=None)


@pytest.mark.endpoint("POST", "/api/v1/actions", "success")
def test_ac_22_cancels_r2_and_keeps_r1() -> None:
    response = _post(_cancel("r2"), "cancel the gym reminder")
    body = response.json()
    assert response.status_code == 200
    assert body["action"]["intent"] == "cancel" and body["action"]["target_reminder_id"] == "r2"
    applied = body["applied"]
    assert applied["operation"] == "cancelled" and applied["affected_id"] == "r2"
    assert applied["new_time"] is None and applied["reminders"] == [R1]


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
@pytest.mark.parametrize("target", ["r9", "R2"], ids=["unknown", "case-changed"])
def test_an_unknown_target_is_502_and_nothing_is_removed(target: str) -> None:
    response = _post(_cancel(target), "cancel the gym reminder")
    body: JsonObject = response.json()
    assert response.status_code == 502 and body["error"]["code"] == "model_output_invalid"
    assert "applied" not in body and "action" not in body
