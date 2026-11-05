"""POST /api/v1/actions for create: applied on success, nothing applied on bad output (FR-1)."""

import pytest
from app_helpers import FixedClock, JsonObject, create_dict
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.llm.stub_client import Scripted, StubLLMClient
from app.settings import Settings

pytestmark = pytest.mark.covers("FR-1", "GR-5", "INV-5", "AC-1")

AC_1 = {
    "text": "remind me to pay rent next Monday at 9am",
    "timezone": "Asia/Kolkata",
    "now": "2026-11-05T10:00:00+05:30",
}
EXISTING = {"id": "r1", "title": "Dentist", "time": "2026-11-06T10:00:00+05:30"}


def _post(scripted: Scripted, **extra: object) -> tuple[int, JsonObject]:
    app = create_app(
        settings=Settings(_env_file=None),
        llm_client=StubLLMClient(scripted),
        clock=FixedClock(),
    )
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/actions", json={**AC_1, **extra}
    )
    return response.status_code, response.json()


@pytest.mark.endpoint("POST", "/api/v1/actions", "success")
def test_ac_1_creates_a_reminder_with_a_store_minted_id() -> None:
    status, body = _post(
        create_dict(title="pay rent", datetime_iso="2026-11-09T09:00:00+05:30"),
        reminders=[EXISTING],
    )
    assert status == 200
    assert body["action"]["intent"] == "create"
    assert body["action"]["datetime_iso"] == "2026-11-09T09:00:00+05:30"
    applied = body["applied"]
    assert applied["operation"] == "created" and applied["affected_id"] == "rem-1"
    created = [r for r in applied["reminders"] if r["id"] == "rem-1"]
    assert created == [{"id": "rem-1", "title": "pay rent", "time": "2026-11-09T09:00:00+05:30"}]
    assert [r["id"] for r in applied["reminders"]] == ["r1", "rem-1"]


@pytest.mark.endpoint("POST", "/api/v1/actions", "failure")
@pytest.mark.parametrize(
    "when",
    ["2026-11-05T09:00:00+05:30", "2026-11-09T09:00:00+00:00"],
    ids=["past-time", "wrong-offset"],
)
def test_a_past_time_or_a_wrong_offset_is_502_and_nothing_is_applied(when: str) -> None:
    status, body = _post(create_dict(datetime_iso=when), reminders=[EXISTING])
    assert status == 502
    assert body["error"]["code"] == "model_output_invalid"
    assert "applied" not in body and "action" not in body
