"""POST /api/v1/actions for reschedule: one reminder moves; bad or unresolved targets move none."""

from typing import Any

import httpx
import pytest
from app_helpers import FixedClock, action_dict
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.llm.stub_client import Scripted, StubLLMClient
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-5", "INV-5", "GR-5", "AC-17", "AC-18", "AC-19")

NOW = "2026-11-05T10:00:00+00:00"
AC_17_REMINDERS = [
    {"id": "r1", "title": "Dentist appointment", "time": "2026-11-06T10:00:00+00:00"},
    {"id": "r2", "title": "Gym session", "time": "2026-11-07T07:00:00+00:00"},
]
AC_19_REMINDERS = [
    {"id": "r3", "title": "Call vendor", "time": "2026-11-06T09:00:00+00:00"},
    {"id": "r4", "title": "Call dentist", "time": "2026-11-06T11:00:00+00:00"},
]


def _post(scripted: Scripted, text: str, reminders: list[dict[str, str]]) -> httpx.Response:
    app = create_app(
        settings=Settings(_env_file=None), llm_client=StubLLMClient(scripted), clock=FixedClock()
    )
    response: httpx.Response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/actions", json={"text": text, "now": NOW, "reminders": reminders}
    )
    return response


def _reschedule(target: str, when: str) -> dict[str, object]:
    return action_dict(
        intent="reschedule",
        target_reminder_id=target,
        datetime_iso=when,
        clarification_question=None,
    )


@pytest.mark.endpoint("POST", "/api/v1/actions", "success")
def test_ac_17_moves_r1_and_leaves_r2_untouched() -> None:
    response = _post(
        _reschedule("r1", "2026-11-06T16:00:00+00:00"),
        "move the dentist one to Friday 4pm",
        AC_17_REMINDERS,
    )
    body = response.json()
    assert response.status_code == 200
    assert body["action"]["intent"] == "reschedule" and body["action"]["target_reminder_id"] == "r1"
    assert body["action"]["datetime_iso"] == "2026-11-06T16:00:00+00:00"
    applied = body["applied"]
    assert applied["operation"] == "rescheduled" and applied["affected_id"] == "r1"
    assert applied["new_time"] == "2026-11-06T16:00:00+00:00"
    assert applied["reminders"] == [
        {"id": "r1", "title": "Dentist appointment", "time": "2026-11-06T16:00:00+00:00"},
        AC_17_REMINDERS[1],
    ]


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
@pytest.mark.parametrize("target", ["r9", "R1"], ids=["unknown", "case-changed"])
def test_an_unknown_target_is_502_and_nothing_is_applied(target: str) -> None:
    response = _post(
        _reschedule(target, "2026-11-06T16:00:00+00:00"), "move the dentist one", AC_17_REMINDERS
    )
    body: dict[str, Any] = response.json()
    assert response.status_code == 502 and body["error"]["code"] == "model_output_invalid"
    assert "applied" not in body and "action" not in body


@pytest.mark.endpoint("POST", "/api/v1/actions", "success")
@pytest.mark.parametrize(
    ("text", "reminders"),
    [
        ("move the yoga reminder to Friday 4pm", AC_17_REMINDERS),
        ("move the call reminder to Friday 4pm", AC_19_REMINDERS),
    ],
    ids=["AC-18-no-match", "AC-19-two-matches"],
)
def test_no_match_or_several_matches_clarify_and_leave_every_reminder_alone(
    text: str, reminders: list[dict[str, str]]
) -> None:
    response = _post(
        action_dict(clarification_question="Which reminder do you mean?"), text, reminders
    )
    body = response.json()
    assert response.status_code == 200
    assert body["action"]["intent"] == "clarify" and body["action"]["target_reminder_id"] is None
    assert body["applied"]["operation"] == "none" and body["applied"]["reminders"] == reminders
