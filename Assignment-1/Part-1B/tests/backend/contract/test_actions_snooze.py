"""POST /api/v1/actions for snooze: the applied time follows FR-6; bad durations apply nothing."""

import httpx
import pytest
from app_helpers import FixedClock, JsonObject, action_dict
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.llm.stub_client import Scripted, StubLLMClient
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-6", "INV-4", "GR-5", "AC-20", "AC-21")

NOW = "2026-11-05T10:00:00+00:00"
R3 = {"id": "r3", "title": "Call vendor", "time": "2026-11-05T11:00:00+00:00"}
R5 = {"id": "r5", "title": "Standup", "time": "2026-11-05T09:00:00+00:00"}
OTHER = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"}


def _post(scripted: Scripted, text: str, reminders: list[dict[str, str]]) -> httpx.Response:
    app = create_app(
        settings=Settings(_env_file=None), llm_client=StubLLMClient(scripted), clock=FixedClock()
    )
    response: httpx.Response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/actions", json={"text": text, "now": NOW, "reminders": reminders}
    )
    return response


def _snooze(target: str, minutes: int) -> dict[str, object]:
    return action_dict(
        intent="snooze",
        target_reminder_id=target,
        snooze_minutes=minutes,
        clarification_question=None,
    )


@pytest.mark.endpoint("POST", "/api/v1/actions", "success")
@pytest.mark.parametrize(
    ("target", "minutes", "text", "reminders", "expected"),
    [
        ("r3", 120, "snooze the vendor call for 2 hours", [R3, OTHER], "2026-11-05T13:00:00+00:00"),
        ("r5", 15, "snooze the standup for 15 minutes", [R5, OTHER], "2026-11-05T10:15:00+00:00"),
    ],
    ids=["AC-20", "AC-21"],
)
def test_snooze_applies_the_fr_6_time_to_one_reminder(
    target: str, minutes: int, text: str, reminders: list[dict[str, str]], expected: str
) -> None:
    response = _post(_snooze(target, minutes), text, reminders)
    body = response.json()
    assert response.status_code == 200
    assert body["action"]["intent"] == "snooze" and body["action"]["target_reminder_id"] == target
    assert body["action"]["snooze_minutes"] == minutes and body["action"]["datetime_iso"] is None
    applied = body["applied"]
    assert applied["operation"] == "snoozed" and applied["affected_id"] == target
    assert applied["new_time"] == expected
    moved = {r["id"]: r["time"] for r in applied["reminders"]}
    assert moved[target] == expected and moved["r1"] == OTHER["time"]


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
@pytest.mark.parametrize("minutes", [0, 1441, -5], ids=["zero", "1441", "negative"])
def test_a_duration_outside_1_to_1440_is_502_and_nothing_is_applied(minutes: int) -> None:
    response = _post(_snooze("r3", minutes), "snooze the vendor call", [R3])
    body: JsonObject = response.json()
    assert response.status_code == 502 and body["error"]["code"] == "model_output_invalid"
    assert "applied" not in body and "action" not in body


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
def test_a_snooze_of_an_unsupplied_reminder_is_502() -> None:
    response = _post(_snooze("r9", 15), "snooze it for 15 minutes", [R3])
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "model_output_invalid"
