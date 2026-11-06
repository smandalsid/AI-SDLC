"""POST /api/v1/actions for clarify: nothing applied; a bad question is a 502 (FR-2, INV-6)."""

import pytest
from app_helpers import FixedClock, JsonObject, action_dict
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.llm.stub_client import Scripted, StubLLMClient
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-2", "FR-3", "INV-6", "AC-4", "AC-5", "AC-6")

NOW = "2026-11-05T10:00:00+00:00"
EXISTING = [
    {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+00:00"},
    {"id": "r2", "title": "Gym session", "time": "2026-11-07T18:00:00+00:00"},
]


def _post(scripted: Scripted, text: str) -> tuple[int, JsonObject]:
    app = create_app(
        settings=Settings(_env_file=None),
        llm_client=StubLLMClient(scripted),
        clock=FixedClock(),
    )
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/actions", json={"text": text, "now": NOW, "reminders": EXISTING}
    )
    return response.status_code, response.json()


@pytest.mark.endpoint("POST", "/api/v1/actions", "success")
@pytest.mark.parametrize(
    ("text", "overrides"),
    [
        (
            "remind me to call the vendor",
            {"title": "call the vendor", "clarification_question": "At what time?"},
        ),
        (
            "remind me tomorrow at 5pm",
            {"clarification_question": "What should I remind you about?"},
        ),
        (
            "remind me to submit the report tomorrow",
            {"title": "submit the report", "clarification_question": "What time of day?"},
        ),
    ],
    ids=["AC-4", "AC-5", "AC-6"],
)
def test_a_clarification_applies_nothing_and_keeps_missing_fields_null(
    text: str, overrides: dict[str, object]
) -> None:
    status, body = _post(action_dict(**overrides), text)
    assert status == 200
    action = body["action"]
    assert action["intent"] == "clarify" and action["clarification_question"]
    assert action["datetime_iso"] is None and action["snooze_minutes"] is None
    assert action["target_reminder_id"] is None and action["refusal_reason"] is None
    assert action["title"] == overrides.get("title")
    assert body["applied"]["operation"] == "none" and body["applied"]["affected_id"] is None
    assert body["applied"]["new_time"] is None and body["applied"]["reminders"] == EXISTING


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
@pytest.mark.parametrize(
    "question",
    [None, "", "q" * 201],
    ids=["missing", "empty", "201-characters"],
)
def test_a_clarification_without_a_usable_question_is_502(question: str | None) -> None:
    status, body = _post(action_dict(clarification_question=question), "remind me")
    assert status == 502
    assert body["error"]["code"] == "model_output_invalid"
    assert "applied" not in body and "action" not in body
